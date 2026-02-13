'''
Information Set Structure for Counterfactual Regret Minimization (CFR)

An information set represents what a player knows at a decision point:
- Their private cards
- Public information (board cards, betting history)
- Their position
- The current street and toss phase state
'''
from collections import defaultdict
from typing import List, Tuple, Optional
import hashlib


class InformationSet:
    '''
    Represents an information set for CFR.

    An information set uniquely identifies a decision point from a player's perspective,
    containing all observable information but not opponent's private cards.
    '''

    def __init__(self,
                 player: int,
                 street: int,
                 hole_cards: Tuple[str, ...],
                 board_cards: Tuple[str, ...],
                 betting_history: str,
                 pot_commitment: Tuple[int, int],
                 toss_phase: Optional[int] = None):
        '''
        Args:
            player: Player index (0 or 1)
            street: Current street (0=preflop, 2=flop+toss, 3=toss, 4=turn, 5=river)
            hole_cards: Player's private cards (sorted tuple)
            board_cards: Community cards visible to all (sorted tuple)
            betting_history: String encoding betting actions (e.g., "r10c" for raise 10, call)
            pot_commitment: (player0_contribution, player1_contribution) to pot
            toss_phase: None for betting rounds, 0/1 for which player is discarding
        '''
        self.player = player
        self.street = street
        self.hole_cards = tuple(sorted(hole_cards))
        self.board_cards = tuple(sorted(board_cards))
        self.betting_history = betting_history
        self.pot_commitment = pot_commitment
        self.toss_phase = toss_phase

        # Create a unique key for this information set
        self.key = self._create_key()

    def _create_key(self) -> str:
        '''
        Creates a unique string key for this information set.
        This key is used as a hash for storing regrets and strategies.
        '''
        # Convert cards to strings (handles both Card objects and strings)
        hole_strs = [str(card) for card in self.hole_cards]
        board_strs = [str(card) for card in self.board_cards]

        components = [
            f"p{self.player}",
            f"s{self.street}",
            f"h{','.join(hole_strs)}",
            f"b{','.join(board_strs)}",
            f"bh{self.betting_history}",
            f"pc{self.pot_commitment[0]},{self.pot_commitment[1]}",
        ]
        if self.toss_phase is not None:
            components.append(f"t{self.toss_phase}")

        key_str = "|".join(components)
        return hashlib.md5(key_str.encode()).hexdigest()

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        if not isinstance(other, InformationSet):
            return False
        return self.key == other.key

    def __repr__(self):
        return f"InfoSet(p{self.player}, s{self.street}, h{self.hole_cards}, b{self.board_cards[:3]}...)"


def create_info_set_from_state(round_state, player: int, betting_history: str = "") -> InformationSet:
    '''
    Creates an InformationSet from a RoundState for a given player.

    Args:
        round_state: The current RoundState
        player: The player index (0 or 1)
        betting_history: String encoding of betting actions so far

    Returns:
        InformationSet for this decision point
    '''
    active = round_state.button % 2
    street = round_state.street

    MAX_HISTORY_LEN = 12
    betting_history = betting_history[-MAX_HISTORY_LEN:]

    # Get player's hole cards (sorted for abstraction)
    # Convert Card objects to strings for consistent hashing
    hole_cards = tuple(sorted(str(card) for card in round_state.hands[player]))

    # Get board cards (sorted)
    # Convert Card objects to strings for consistent hashing
    board_cards = tuple(sorted(str(card) for card in round_state.board))

    # Get pot commitments
    pot_commitment = (round_state.pips[0], round_state.pips[1])

    # Determine toss phase
    toss_phase = None
    if street in (2, 3):
        # Street 2: Big Blind (player 1) discards first
        # Street 3: Dealer (player 0) discards second
        toss_phase = street % 2

    return InformationSet(
        player=player,
        street=street,
        hole_cards=hole_cards,
        board_cards=board_cards,
        betting_history=betting_history,
        pot_commitment=pot_commitment,
        toss_phase=toss_phase
    )


def abstract_hand_strength(hole_cards: Tuple[str, ...], board_cards: Tuple[str, ...]) -> int:
    '''
    Abstract hand strength into buckets for memory efficiency.

    This is a simplified abstraction - in practice, you might want more sophisticated
    bucketing based on hand strength, potential, etc.

    Returns:
        Integer bucket (0-9) representing hand strength category
    '''
    # Simple abstraction: count high cards and pairs
    ranks = "23456789TJQKA"
    hole_ranks = [ranks.index(c[0]) for c in hole_cards]
    board_ranks = [ranks.index(c[0]) for c in board_cards] if board_cards else []

    all_ranks = hole_ranks + board_ranks

    # Count pairs
    rank_counts = {}
    for r in all_ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1

    pairs = sum(1 for count in rank_counts.values() if count >= 2)
    high_cards = sum(1 for r in hole_ranks if r >= ranks.index('T'))

    # Simple bucketing
    if pairs >= 2:
        bucket = 8  # Two pair or better
    elif pairs == 1:
        bucket = 4 + min(high_cards, 3)
    else:
        bucket = min(high_cards, 3)

    return min(bucket, 9)


def create_abstracted_info_set(round_state, player: int, betting_history: str = "",
                                use_abstraction: bool = True) -> InformationSet:
    '''
    Creates an InformationSet with optional hand strength abstraction.

    If use_abstraction is True, hole cards are abstracted into strength buckets
    to reduce the number of information sets.
    '''
    if not use_abstraction:
        return create_info_set_from_state(round_state, player, betting_history)

    # Abstract hole cards by strength bucket
    hole_cards = tuple(sorted(round_state.hands[player]))
    board_cards = tuple(sorted(round_state.board))
    strength_bucket = abstract_hand_strength(hole_cards, board_cards)

    # Use bucket as a simplified representation
    # In practice, you might want to preserve more information
    abstracted_hole = tuple([f"{strength_bucket}_bucket"] * len(hole_cards))

    active = round_state.button % 2
    street = round_state.street
    pot_commitment = (round_state.pips[0], round_state.pips[1])
    toss_phase = None
    if street in (2, 3):
        toss_phase = street % 2

    return InformationSet(
        player=player,
        street=street,
        hole_cards=abstracted_hole,
        board_cards=board_cards,
        betting_history=betting_history,
        pot_commitment=pot_commitment,
        toss_phase=toss_phase
    )
