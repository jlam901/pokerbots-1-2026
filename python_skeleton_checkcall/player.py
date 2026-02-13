'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import CallAction, CheckAction, DiscardAction, FoldAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot
from pathlib import Path
import os
import re
import sys
import time


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.
        '''
        self._progress_interval = 1000
        self._last_progress = 0
        self._progress_path = Path(__file__).resolve().parent / "progress.txt"
        self._round_num = 0
        self._total_rounds = self._load_total_rounds()
        self._is_progress_owner = self._acquire_progress_owner()

    def _log_progress(self, message: str) -> None:
        print(message)
        sys.stdout.flush()
        try:
            with self._progress_path.open("a") as handle:
                handle.write(message + "\n")
        except OSError:
            pass

    def _load_total_rounds(self) -> int | None:
        config_path = Path(__file__).resolve().parents[1] / "config.py"
        try:
            content = config_path.read_text()
        except OSError:
            return None
        match = re.search(r"^\s*NUM_ROUNDS\s*=\s*(\d+)\s*$", content, re.MULTILINE)
        if not match:
            return None
        return int(match.group(1))

    def _acquire_progress_owner(self) -> bool:
        lock_path = Path(__file__).resolve().parent / "progress_owner.lock"
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as handle:
                handle.write(str(os.getpid()))
            return True
        except FileExistsError:
            try:
                mtime = lock_path.stat().st_mtime
            except OSError:
                return False
            if time.time() - mtime > 60:
                try:
                    lock_path.unlink()
                except OSError:
                    return False
                return self._acquire_progress_owner()
            return False

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
        if self._is_progress_owner:
            self._round_num += 1
            round_num = self._round_num
            if round_num == 1 or round_num - self._last_progress >= self._progress_interval:
                if self._total_rounds:
                    pct = (round_num / self._total_rounds) * 100
                    self._log_progress(f"Progress: {round_num}/{self._total_rounds} ({pct:.2f}%)")
                else:
                    self._log_progress(f"Progress: {round_num} rounds")
                self._last_progress = round_num

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
        if self._is_progress_owner and active == 0 and self._total_rounds and self._round_num == self._total_rounds:
            self._log_progress(f"Progress: {self._total_rounds}/{self._total_rounds} (100.00%)")

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
        legal_actions = round_state.legal_actions()
        my_cards= round_state.hands[active]
        board_cards = round_state.board

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

        if CheckAction in legal_actions:
            return CheckAction()

        if CallAction in legal_actions:
            return CallAction()

        if FoldAction in legal_actions:
            return FoldAction()

        return CheckAction()






if __name__ == '__main__':
    run_bot(Player(), parse_args())
