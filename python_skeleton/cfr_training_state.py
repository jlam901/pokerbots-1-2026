'''
Training-specific RoundState wrapper that handles card dealing simulation.

The skeleton's RoundState doesn't include deck/dealing, so we simulate it for training.
'''
import pkrbot
from functools import lru_cache
from skeleton.states import RoundState, TerminalState, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction


class TrainingRoundState:
    '''
    Wrapper around RoundState that simulates card dealing for training.
    '''

    def __init__(self, round_state: RoundState, deck: pkrbot.Deck = None):
        '''
        Args:
            round_state: The underlying RoundState
            deck: Optional deck for simulation (creates new one if None)
        '''
        self.round_state = round_state
        if deck is None:
            self.deck = pkrbot.Deck()
            self.deck.shuffle()
        else:
            self.deck = deck

    def __getattr__(self, name):
        '''Delegate attribute access to underlying round_state.'''
        return getattr(self.round_state, name)

    def proceed_street(self):
        '''
        Advances to next street, dealing cards as needed.

        Returns:
            New TrainingRoundState or TerminalState
        '''
        # Deal cards based on street
        new_board = list(self.round_state.board)
        new_street = self.round_state.street

        if self.round_state.street == 0:
            # After pre-flop: deal 2 cards (flop) + start toss phase
            new_street = 2
            # Deal 2 cards for flop
            flop_cards = self.deck.deal(2)
            new_board.extend([str(card) for card in flop_cards])
        elif self.round_state.street == 2:
            # After first discard: second player discards
            new_street = 3
        elif self.round_state.street == 3:
            # After second discard: deal turn
            new_street = 4
            turn_card = self.deck.deal(1)[0]
            new_board.append(str(turn_card))
        elif self.round_state.street == 4:
            # After turn betting: deal river
            new_street = 5
            river_card = self.deck.deal(1)[0]
            new_board.append(str(river_card))
        elif self.round_state.street == 5:
            # After river betting: showdown
            new_street = 6

        if new_street == 6:
            # Showdown with evaluation
            return self._showdown()

        # Determine button based on street
        if new_street == 2:
            button = 1  # Big Blind discards first
        elif new_street == 3:
            button = 0  # Dealer discards second
        else:
            button = 1  # Big Blind acts first after discard phase

        new_round_state = RoundState(
            button, new_street, [0, 0],
            self.round_state.stacks,
            self.round_state.hands,
            new_board,
            self.round_state
        )

        return TrainingRoundState(new_round_state, self.deck)

    def _showdown(self) -> TerminalState:
        '''
        Evaluates hands and returns terminal state with deltas.
        '''
        board = [str(card) for card in self.round_state.board]
        hand0 = [str(card) for card in self.round_state.hands[0]]
        hand1 = [str(card) for card in self.round_state.hands[1]]

        score0 = _evaluate_cached(board + hand0)
        score1 = _evaluate_cached(board + hand1)

        if score0 > score1:
            delta = self._get_delta(0)
        elif score1 > score0:
            delta = self._get_delta(1)
        else:
            delta = 0

        return TerminalState([int(delta), -int(delta)], self.round_state)

    def _get_delta(self, winner_index: int) -> int:
        '''
        Mirrors engine delta calculation for training.
        '''
        if winner_index == 0:
            return STARTING_STACK - self.round_state.stacks[1]
        return self.round_state.stacks[0] - STARTING_STACK

    def proceed(self, action):
        '''
        Advances state by one action.

        Args:
            action: Action to take

        Returns:
            New TrainingRoundState or TerminalState
        '''
        new_state = self.round_state.proceed(action)

        if isinstance(new_state, TerminalState):
            return new_state

        # Check if we need to advance street (after betting round completes)
        # This is handled by proceed_street in the actual proceed logic
        # But we need to handle card dealing

        return TrainingRoundState(new_state, self.deck)

    @staticmethod
    def create_initial():
        '''
        Creates initial training state.

        Returns:
            Initial TrainingRoundState
        '''
        deck = pkrbot.Deck()
        deck.shuffle()

        hands = [deck.deal(3), deck.deal(3)]
        board = []
        pips = [SMALL_BLIND, BIG_BLIND]
        stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]

        round_state = RoundState(0, 0, pips, stacks, hands, board, None)
        return TrainingRoundState(round_state, deck)


@lru_cache(maxsize=250_000)
def _evaluate_cached_key(cards_tuple):
    '''
    Cached wrapper around pkrbot.evaluate for speed during training.
    '''
    cards = list(cards_tuple)
    return pkrbot.evaluate(cards)


def _evaluate_cached(cards_list):
    key = tuple(sorted(cards_list))
    return _evaluate_cached_key(key)
