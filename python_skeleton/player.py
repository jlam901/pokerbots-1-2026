'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import csv
import os
from itertools import combinations


RANK_ORDER = "23456789TJQKA"

# Post-flop hand strength -> (target_contribution, max_total for round; None = all-in)
POSTFLOP_TARGET_MAX = {
    "quads": (100, None),
    "full_house": (100, None),
    "flush": (75, None),
    "straight": (50, None),
    "trips": (40, None),
    "two_pair": (35, 200),
    "top_pair": (30, 200),
    "second_pair": (10, 100),
    "nothing": (0, 10),
}

# Hand strength order (weakest to strongest) for fold-vs-history logic
HAND_STRENGTH_ORDER = (
    "nothing",
    "second_pair",
    "top_pair",
    "two_pair",
    "trips",
    "straight",
    "flush",
    "full_house",
    "quads",
)


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        base_dir = os.path.dirname(__file__)
        self.preflop_chart_offsuit = self._load_preflop_chart(
            os.path.join(base_dir, "preflop_chart_offsuit.csv")
        )
        self.preflop_chart_suited_two = self._load_preflop_chart(
            os.path.join(base_dir, "preflop_chart_suited_two.csv")
        )
        self.preflop_chart_suited_three = self._load_preflop_chart(
            os.path.join(base_dir, "preflop_chart_suited_three.csv")
        )
        # Per-hand-strength target and max (updated during play)
        self._target_contribution = {k: v[0] for k, v in POSTFLOP_TARGET_MAX.items()}
        self._max_call = {k: v[1] for k, v in POSTFLOP_TARGET_MAX.items()}
        # Opponent bet history (amount they have in the round when they raised us)
        self._opponent_bet_history = []
        self._we_raised_this_round = False
        self._current_hand_category = None

    @staticmethod
    def _load_preflop_chart(path):
        '''Load a preflop CSV chart into a dict of hand -> win_pct.'''
        chart = {}
        try:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hand = row["hand"].strip()
                    if not hand:
                        continue
                    try:
                        win_pct = float(row["win_pct"])
                    except (KeyError, ValueError):
                        continue
                    chart[hand] = win_pct
        except OSError:
            # If loading fails, leave chart empty; we'll fall back to neutral strategy.
            chart = {}
        return chart

    def _get_preflop_win_pct(self, my_cards):
        '''Return preflop win percentage for a 3-card hand using the correct chart.'''
        ranks = [card[0] for card in my_cards]
        suits = [card[1] for card in my_cards]

        # Sort ranks from highest to lowest according to RANK_ORDER
        ranks_sorted = sorted(ranks, key=lambda r: RANK_ORDER.index(r), reverse=True)
        hand_key = "".join(ranks_sorted)

        unique_suits = len(set(suits))
        if unique_suits == 1:
            chart = self.preflop_chart_suited_three
        elif unique_suits == 2:
            chart = self.preflop_chart_suited_two
        else:
            chart = self.preflop_chart_offsuit

        win_pct = chart.get(hand_key)
        # If we don't find the hand for some reason, fall back to a neutral 50%
        if win_pct is None:
            return 50.0
        return win_pct

    def _choose_preflop_action(self, round_state, legal_actions, my_pip, opp_pip, my_stack, win_pct):
        '''Preflop betting strategy based on our estimated win probability.'''
        continue_cost = opp_pip - my_pip

        # Case 1: very weak hand, win_pct < 50
        if win_pct < 50.0:
            if continue_cost <= 0 and CheckAction in legal_actions:
                return CheckAction()
            if 0 < continue_cost <= 8 and CallAction in legal_actions:
                return CallAction()
            if FoldAction in legal_actions and continue_cost > 0:
                return FoldAction()
            # Fallback: check or call if that's all we can do
            if CheckAction in legal_actions:
                return CheckAction()
            if CallAction in legal_actions:
                return CallAction()

        # Case 2: marginal hand, 50 <= win_pct < 60
        if 50.0 <= win_pct < 60.0:
            if continue_cost <= 0 and CheckAction in legal_actions:
                return CheckAction()
            if 0 < continue_cost <= 20 and CallAction in legal_actions:
                return CallAction()
            if FoldAction in legal_actions and continue_cost > 0:
                return FoldAction()
            if CheckAction in legal_actions:
                return CheckAction()
            if CallAction in legal_actions:
                return CallAction()

        # Helper for more aggressive tiers
        def aggressive_preflop(target_contribution, max_total=None):
            nonlocal continue_cost

            # If there's a cap and calling would exceed it, fold
            if max_total is not None and continue_cost > 0:
                if my_pip + continue_cost > max_total:
                    if FoldAction in legal_actions:
                        return FoldAction()

            # Try to reach at least target_contribution for this round
            # First see what calling would do
            projected_pip_if_call = my_pip + max(continue_cost, 0)

            # Decide whether to raise
            if RaiseAction in legal_actions and my_stack > continue_cost:
                min_raise, max_raise = round_state.raise_bounds()

                # Desired total contribution after raise
                desired_total = max(target_contribution, projected_pip_if_call)

                # Respect max_raise and optional max_total cap
                raise_to = desired_total
                if raise_to < min_raise:
                    raise_to = min_raise
                if raise_to > max_raise:
                    raise_to = max_raise
                if max_total is not None and raise_to > max_total:
                    raise_to = max_total

                # Only raise if it actually increases our contribution and we can afford it
                if raise_to > my_pip and raise_to - my_pip <= my_stack and min_raise <= raise_to <= max_raise:
                    return RaiseAction(raise_to)

            # If we didn't raise, fall back to calling/checking within limits
            if continue_cost <= 0 and CheckAction in legal_actions:
                return CheckAction()
            if continue_cost > 0 and CallAction in legal_actions:
                # If there's a cap, ensure we respect it
                if max_total is None or my_pip + continue_cost <= max_total:
                    return CallAction()
            if FoldAction in legal_actions and continue_cost > 0:
                return FoldAction()
            if CheckAction in legal_actions:
                return CheckAction()
            if CallAction in legal_actions:
                return CallAction()
            return None

        # Case 3: decent hand, 60 <= win_pct < 70
        if 60.0 <= win_pct < 70.0:
            action = aggressive_preflop(target_contribution=10, max_total=160)
            if action is not None:
                return action

        # Case 4: strong hand, 70 <= win_pct < 80
        if 70.0 <= win_pct < 80.0:
            action = aggressive_preflop(target_contribution=20, max_total=400)
            if action is not None:
                return action

        # Case 5: very strong hand, 80 <= win_pct < 90
        if 80.0 <= win_pct < 90.0:
            action = aggressive_preflop(target_contribution=30, max_total=None)
            if action is not None:
                return action

        # Case 6: monster hand, win_pct >= 90
        if win_pct >= 90.0:
            action = aggressive_preflop(target_contribution=50, max_total=None)
            if action is not None:
                return action

        # As a very last resort, default to a simple check/call preference
        if continue_cost <= 0 and CheckAction in legal_actions:
            return CheckAction()
        if CallAction in legal_actions:
            return CallAction()
        if CheckAction in legal_actions:
            return CheckAction()
        if FoldAction in legal_actions:
            return FoldAction()
        return CallAction()  # fallback

    @staticmethod
    def _rank_value(rank):
        """Return numeric value for rank (2=0, A=12)."""
        return RANK_ORDER.index(rank)

    def _evaluate_five_cards(self, cards):
        """
        Evaluate a 5-card hand. Returns (category, tiebreak) for comparison.
        category: quads, full_house, flush, straight, trips, two_pair, one_pair, high_card
        For one_pair we need to distinguish top_pair vs second_pair later using board.
        """
        ranks = [c[0] for c in cards]
        suits = [c[1] for c in cards]
        rank_vals = sorted([self._rank_value(r) for r in ranks], reverse=True)
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        count_list = sorted(rank_counts.values(), reverse=True)
        is_flush = len(set(suits)) == 1
        # Straight: sort values, check for 5 consecutive; handle A-2-3-4-5 (wheel)
        sorted_vals = sorted(set(rank_vals), reverse=True)
        is_straight = False
        straight_high = -1
        if len(sorted_vals) >= 5:
            for i in range(len(sorted_vals) - 4):
                run = sorted_vals[i : i + 5]
                if run[0] - run[4] == 4:
                    is_straight = True
                    straight_high = run[0]
                    break
            # wheel: A-2-3-4-5 (12,0,1,2,3)
            if not is_straight and 12 in sorted_vals:
                if all(v in sorted_vals for v in [0, 1, 2, 3]):
                    is_straight = True
                    straight_high = 3  # 5 high

        if count_list[0] == 4:
            return ("quads", rank_vals)
        if count_list[0] == 3 and count_list[1] >= 2:
            return ("full_house", rank_vals)
        if is_flush:
            return ("flush", rank_vals)
        if is_straight:
            return ("straight", rank_vals)
        if count_list[0] == 3:
            return ("trips", rank_vals)
        if count_list[0] == 2 and count_list[1] == 2:
            return ("two_pair", rank_vals)
        if count_list[0] == 2:
            return ("one_pair", rank_vals)
        return ("high_card", rank_vals)

    def _evaluate_postflop_hand(self, my_cards, board_cards):
        """
        Find best 5-card hand from my_cards (2) + board_cards (4, 5, or 6).
        Returns category: quads, full_house, flush, straight, trips, two_pair, top_pair, second_pair, nothing.
        """
        all_cards = list(my_cards) + list(board_cards)
        if len(all_cards) < 5:
            return "nothing"
        category_order = (
            "high_card",
            "one_pair",
            "two_pair",
            "trips",
            "straight",
            "flush",
            "full_house",
            "quads",
        )
        def pair_rank_from_five(five_cards):
            ranks = [c[0] for c in five_cards]
            for r in set(ranks):
                if ranks.count(r) == 2:
                    return r
            return None

        best_category = "high_card"
        best_tiebreak = []
        best_pair_rank = None

        for five in combinations(all_cards, 5):
            five_list = list(five)
            cat, tiebreak = self._evaluate_five_cards(five_list)
            if category_order.index(cat) > category_order.index(best_category):
                best_category = cat
                best_tiebreak = tiebreak
                best_pair_rank = pair_rank_from_five(five_list) if cat == "one_pair" else None
            elif cat == best_category and tiebreak > best_tiebreak:
                best_tiebreak = tiebreak
                if cat == "one_pair":
                    best_pair_rank = pair_rank_from_five(five_list)

        if best_category == "one_pair":
            # Classify as top_pair, second_pair, or nothing (pair below 2nd on board)
            board_ranks = [c[0] for c in board_cards]
            board_rank_vals = sorted(
                set(self._rank_value(r) for r in board_ranks), reverse=True
            )
            if len(board_rank_vals) < 2:
                return "top_pair"  # only one rank on board
            pair_val = self._rank_value(best_pair_rank) if best_pair_rank else -1
            if pair_val == board_rank_vals[0]:
                return "top_pair"
            if pair_val == board_rank_vals[1]:
                return "second_pair"
            return "nothing"
        if best_category == "high_card":
            return "nothing"
        return best_category

    def _choose_postflop_action(
        self, round_state, legal_actions, my_pip, opp_pip, my_stack, target_contribution, max_total
    ):
        """Play post-flop by target contribution and max call for the round (core rule)."""
        continue_cost = opp_pip - my_pip
        # max_total None = all-in (no cap)
        if max_total is not None and continue_cost > 0:
            if my_pip + continue_cost > max_total:
                if FoldAction in legal_actions:
                    return FoldAction()
        projected_pip_if_call = my_pip + max(continue_cost, 0)
        if RaiseAction in legal_actions and my_stack > continue_cost:
            min_raise, max_raise = round_state.raise_bounds()
            desired_total = max(target_contribution, projected_pip_if_call)
            raise_to = desired_total
            if raise_to < min_raise:
                raise_to = min_raise
            if raise_to > max_raise:
                raise_to = max_raise
            if max_total is not None and raise_to > max_total:
                raise_to = max_total
            if raise_to > my_pip and raise_to - my_pip <= my_stack and min_raise <= raise_to <= max_raise:
                return RaiseAction(raise_to)
        if continue_cost <= 0 and CheckAction in legal_actions:
            return CheckAction()
        if continue_cost > 0 and CallAction in legal_actions:
            if max_total is None or my_pip + continue_cost <= max_total:
                return CallAction()
        if FoldAction in legal_actions and continue_cost > 0:
            return FoldAction()
        if CheckAction in legal_actions:
            return CheckAction()
        if CallAction in legal_actions:
            return CallAction()
        return CallAction()

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # the total number of seconds your bot has left to play this game
        game_clock = game_state.game_clock
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind
        self._we_raised_this_round = False
        self._current_hand_category = None

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0,2,3,4,5,6 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        # opponent's cards or [] if not revealed
        opp_cards = previous_state.hands[1-active]

        # Update target for this hand strength if we had raised this round
        if self._we_raised_this_round and self._current_hand_category is not None:
            cat = self._current_hand_category
            if cat not in self._target_contribution:
                pass
            else:
                tar = self._target_contribution[cat]
                # Opponent was to act (they folded) <=> previous_state.button % 2 != active
                if previous_state.button % 2 != active:
                    tar = tar * 0.8
                else:
                    tar = tar * 1.2
                tar = max(0, min(int(round(tar)), STARTING_STACK))
                self._target_contribution[cat] = tar

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take

        # Priority: if we're ahead by more than (remaining rounds) * 1.5, fold at soonest moment
        remaining_rounds = NUM_ROUNDS - game_state.round_num
        lock_in_threshold = remaining_rounds * 3 / 2
        if game_state.bankroll > lock_in_threshold and FoldAction in legal_actions:
            return FoldAction()

        # 0, 2, 3, 4, 5, 6 representing pre-flop, bb discard, sb discard, post
        # discard flop betting, and then turn and river
        street = round_state.street
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.board  # the board cards
        # the number of chips you have contributed to the pot this round of betting
        my_pip = round_state.pips[active]
        # the number of chips your opponent has contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]
        # the number of chips you have remaining
        my_stack = round_state.stacks[active]
        # the number of chips your opponent has remaining
        opp_stack = round_state.stacks[1-active]
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        # the number of chips you have contributed to the pot
        my_contribution = STARTING_STACK - my_stack
        # the number of chips your opponent has contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack

        # Preflop strategy using preflop charts
        if street == 0:
            win_pct = self._get_preflop_win_pct(my_cards)
            return self._choose_preflop_action(
                round_state=round_state,
                legal_actions=legal_actions,
                my_pip=my_pip,
                opp_pip=opp_pip,
                my_stack=my_stack,
                win_pct=win_pct,
            )

        # Only use DiscardAction if it's in legal_actions (which already checks street)
        # legal_actions() returns DiscardAction only when street is 2 or 3
        
        if DiscardAction in legal_actions:
            # Combine player's cards and board cards
            all_cards = my_cards + board_cards
            
            # Extract ranks and suits from all cards
            rank_order = "23456789TJQKA"
            all_ranks = [card[0] for card in all_cards]
            all_suits = [card[1] for card in all_cards]
            my_ranks = [card[0] for card in my_cards]
            my_suits = [card[1] for card in my_cards]
            
            # Count occurrences of each rank
            rank_counts = {}
            for rank in all_ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
            # Check if player has 3 of the same card
            for rank in my_ranks:
                if rank_counts[rank] >= 3:
                    # Check if all 3 of my cards are the same rank
                    if my_ranks.count(rank) == 3:
                        return DiscardAction(0)
            
            # Check for flush draws (4 cards of the same suit)
            cards_in_flush_draw = set()
            suit_counts = {}
            for i, suit in enumerate(all_suits):
                suit_counts[suit] = suit_counts.get(suit, 0) + 1
            
            # Find suits with 4 cards (flush draw)
            flush_draw_suits = [suit for suit, count in suit_counts.items() if count == 4]
            if flush_draw_suits:
                flush_suit = flush_draw_suits[0]
                # Mark which of my cards are part of the flush draw
                for i, suit in enumerate(my_suits):
                    if suit == flush_suit:
                        cards_in_flush_draw.add(i)
            
            # Check for open-ended straight draws
            cards_in_straight_draw = set()
            # Convert ranks to numeric values for easier comparison
            rank_to_value = {rank: i for i, rank in enumerate(rank_order)}
            all_rank_values = sorted(set([rank_to_value[rank] for rank in all_ranks]))
            
            # Check for open-ended straight draws (4 consecutive ranks)
            for start_idx in range(len(all_rank_values) - 3):
                consecutive_ranks = all_rank_values[start_idx:start_idx + 4]
                # Check if they form 4 consecutive ranks (difference of 3 between first and last)
                if consecutive_ranks[-1] - consecutive_ranks[0] == 3:
                    first_rank_val = consecutive_ranks[0]
                    last_rank_val = consecutive_ranks[-1]
                    
                    # Check if it's open-ended (can be completed on either end)
                    # Can extend left if first_rank > 0 (not Ace)
                    can_extend_left = first_rank_val > 0
                    # Can extend right if last_rank < 12 (not King)
                    can_extend_right = last_rank_val < len(rank_order) - 1
                    
                    # Open-ended means we can complete on at least one end
                    if can_extend_left or can_extend_right:
                        # This is an open-ended straight draw
                        # Find which of my cards are part of this draw
                        draw_ranks = [rank_order[val] for val in consecutive_ranks]
                        for i, rank in enumerate(my_ranks):
                            if rank in draw_ranks:
                                cards_in_straight_draw.add(i)
            
            # If we have flush draw or straight draw, discard weakest card NOT in draws
            cards_in_draws = cards_in_flush_draw | cards_in_straight_draw
            if cards_in_draws:
                weakest_index = None
                weakest_rank_value = -1
                
                for i, rank in enumerate(my_ranks):
                    if i not in cards_in_draws:  # This card is not part of any draw
                        rank_value = rank_order.index(rank)
                        if weakest_index is None or rank_value < weakest_rank_value:
                            weakest_index = i
                            weakest_rank_value = rank_value
                
                # If all cards are in draws, discard the weakest one overall
                if weakest_index is None:
                    weakest_index = 0
                    weakest_rank_value = rank_order.index(my_ranks[0])
                    for i, rank in enumerate(my_ranks):
                        rank_value = rank_order.index(rank)
                        if rank_value < weakest_rank_value:
                            weakest_index = i
                            weakest_rank_value = rank_value
                
                return DiscardAction(weakest_index)
            
            # Fall back to pair logic if no draws
            # Find which of my cards are part of pairs (or better)
            cards_in_pairs = set()
            for i, rank in enumerate(my_ranks):
                if rank_counts[rank] >= 2:  # This card is part of a pair or better
                    cards_in_pairs.add(i)
            
            # Find the weakest card that is NOT in any pair
            weakest_index = None
            weakest_rank_value = -1
            
            for i, rank in enumerate(my_ranks):
                if i not in cards_in_pairs:  # This card is not part of any pair
                    rank_value = rank_order.index(rank)
                    if weakest_index is None or rank_value < weakest_rank_value:
                        weakest_index = i
                        weakest_rank_value = rank_value
            
            # If all cards are in pairs, discard the weakest one overall
            if weakest_index is None:
                weakest_index = 0
                weakest_rank_value = rank_order.index(my_ranks[0])
                for i, rank in enumerate(my_ranks):
                    rank_value = rank_order.index(rank)
                    if rank_value < weakest_rank_value:
                        weakest_index = i
                        weakest_rank_value = rank_value
            
            return DiscardAction(weakest_index)

        # Post-flop (streets 4, 5, 6): evaluate hand and play by target/max
        if street in (4, 5, 6):
            # Record opponent's bet when they have put more than us this round
            if continue_cost > 0:
                self._opponent_bet_history.append(opp_pip)

            category = self._evaluate_postflop_hand(my_cards, board_cards)
            self._current_hand_category = category

            # Fold vs opponent bet history: only when top 10% of their bets >= 50 chips
            hist = self._opponent_bet_history
            if len(hist) >= 10 and FoldAction in legal_actions and continue_cost > 0:
                sorted_hist = sorted(hist)
                p90_idx = int(0.9 * len(sorted_hist))
                if p90_idx < len(sorted_hist) and sorted_hist[p90_idx] > 80:
                    p90 = sorted_hist[p90_idx]
                    p80 = sorted_hist[int(0.8 * len(sorted_hist))]
                    p70 = sorted_hist[int(0.7 * len(sorted_hist))]
                    cat_idx = HAND_STRENGTH_ORDER.index(category) if category in HAND_STRENGTH_ORDER else 0
                    if opp_pip > p90 and cat_idx < HAND_STRENGTH_ORDER.index("straight"):
                        return FoldAction()
                    if opp_pip > p80 and cat_idx < HAND_STRENGTH_ORDER.index("trips"):
                        return FoldAction()
                    if opp_pip > p70 and cat_idx < HAND_STRENGTH_ORDER.index("two_pair"):
                        return FoldAction()

            target = self._target_contribution.get(category, 0)
            max_call = self._max_call.get(category, 5)
            max_total = max_call  # None = all-in (no cap)
            action = self._choose_postflop_action(
                round_state, legal_actions, my_pip, opp_pip, my_stack, target, max_total
            )
            if isinstance(action, RaiseAction):
                self._we_raised_this_round = True
            return action

        # Fallback for street 2/3 when not discarding: check/call (no random fold/raise)
        if CheckAction in legal_actions:
            return CheckAction()
        if CallAction in legal_actions:
            return CallAction()
        if FoldAction in legal_actions:
            return FoldAction()
        return CallAction()


if __name__ == '__main__':
    run_bot(Player(), parse_args())
