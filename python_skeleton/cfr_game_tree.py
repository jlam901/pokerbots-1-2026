'''
Game Tree Traversal for CFR

Handles the game tree structure, including:
- Chance nodes (card dealing)
- Player decision nodes
- Terminal nodes (showdown, fold)
'''
from typing import List, Tuple, Optional, Dict
import random
import pkrbot
from skeleton.states import RoundState, TerminalState, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction


class GameTree:
    '''
    Manages game tree traversal for CFR training.
    '''

    def __init__(self):
        self.deck = None

    def create_initial_state(self):
        '''
        Creates the initial game state (pre-flop, after blinds posted).

        For training, we use TrainingRoundState which simulates card dealing.

        Returns:
            Initial TrainingRoundState
        '''
        from cfr_training_state import TrainingRoundState
        return TrainingRoundState.create_initial()

    def is_terminal(self, state) -> bool:
        '''
        Checks if a state is terminal.

        Args:
            state: RoundState or TerminalState

        Returns:
            True if terminal
        '''
        return isinstance(state, TerminalState)

    def get_legal_actions(self, state: RoundState) -> List:
        '''
        Gets legal actions for the current state.

        Args:
            state: Current RoundState

        Returns:
            List of legal action objects
        '''
        legal_action_types = state.legal_actions()
        actions = []

        active = state.button % 2

        # Handle discard actions
        if DiscardAction in legal_action_types:
            # Can discard any of the cards in hand
            num_cards = len(state.hands[active])
            for i in range(num_cards):
                actions.append(DiscardAction(i))

        # Handle betting actions
        if FoldAction in legal_action_types:
            actions.append(FoldAction())
        if CallAction in legal_action_types:
            actions.append(CallAction())
        if CheckAction in legal_action_types:
            actions.append(CheckAction())
        if RaiseAction in legal_action_types:
            min_raise, max_raise = state.raise_bounds()
            # Use only min-raise and max-raise (all-in) to limit branching
            raise_sizes = self._get_abstracted_raise_sizes(min_raise, max_raise, state)
            for size in raise_sizes:
                actions.append(RaiseAction(size))

        return actions

    def _get_abstracted_raise_sizes(self, min_raise: int, max_raise: int, state: RoundState) -> List[int]:
        '''
        Abstracts raise sizes to reduce action space.

        Args:
            min_raise: Minimum legal raise
            max_raise: Maximum legal raise
            state: Current state for pot calculation

        Returns:
            List of abstracted raise sizes
        '''
        if min_raise >= max_raise:
            return [min_raise]

        # Keep only min-raise and max-raise (all-in) to cap branching factor.
        return sorted({min_raise, max_raise})

    def get_utility(self, terminal_state: TerminalState, player: int) -> float:
        '''
        Gets utility (payoff) for a player at a terminal state.

        Args:
            terminal_state: Terminal state
            player: Player index

        Returns:
            Utility value (chip delta)
        '''
        return float(terminal_state.deltas[player])

    def sample_chance_outcomes(self, state: RoundState) -> List[Tuple[RoundState, float]]:
        '''
        Samples chance outcomes (card dealing) and returns possible next states.

        In practice, for CFR we might sample a subset of outcomes or use
        expected values. This returns all possible outcomes with probabilities.

        Args:
            state: Current state before chance event

        Returns:
            List of (next_state, probability) tuples
        '''
        # For efficiency, we'll sample a single outcome during training
        # In full CFR, you'd enumerate all possibilities
        next_state = self._advance_chance(state)
        return [(next_state, 1.0)]

    def _advance_chance(self, state: RoundState) -> RoundState:
        '''
        Advances through chance nodes (card dealing).

        For the skeleton version, proceed_street handles card dealing internally.
        We just call it to advance the state.

        Args:
            state: State before chance event

        Returns:
            State after chance event
        '''
        # Street progression handles card dealing
        # The skeleton's proceed_street doesn't actually deal cards (no deck),
        # but it advances the street appropriately
        return state.proceed_street()


def evaluate_hand(hole_cards: List[str], board_cards: List[str]) -> int:
    '''
    Evaluates a poker hand using pkrbot.

    Args:
        hole_cards: Player's hole cards
        board_cards: Community cards

    Returns:
        Hand strength score (higher is better)
    '''
    all_cards = hole_cards + board_cards
    return pkrbot.evaluate(all_cards)
