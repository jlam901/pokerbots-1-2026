'''
CFR-based Poker Bot Player

Uses trained CFR strategy for decision-making during live play.
'''
import random
import os
from cfr_core import CFRAlgorithm
from cfr_info_set import create_info_set_from_state, InformationSet
from skeleton.bot import Bot
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction


class CFRPlayer(Bot):
    '''
    Poker bot that uses Counterfactual Regret Minimization strategy.
    '''

    def __init__(self, strategy_path: str = "cfr_strategy.pkl"):
        '''
        Args:
            strategy_path: Path to saved CFR strategy file
        '''
        self.cfr = CFRAlgorithm()
        self.strategy_path = strategy_path

        # Load strategy if it exists
        if os.path.exists(strategy_path):
            self.cfr.load(strategy_path)
            print(f"Loaded CFR strategy from {strategy_path}")
            print(f"Strategy contains {len(self.cfr.nodes)} information sets")
        else:
            print(f"Warning: Strategy file {strategy_path} not found. Using uniform strategy.")

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts.
        '''
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends.
        '''
        pass

    def get_action(self, game_state, round_state, active):
        '''
        Gets action using CFR strategy.

        Args:
            game_state: GameState object
            round_state: RoundState object
            active: Player index

        Returns:
            Action to take
        '''
        # Get legal actions
        legal_actions = round_state.legal_actions()

        # Build betting history from round state
        betting_history = self._extract_betting_history(round_state)

        # Create information set
        info_set = create_info_set_from_state(round_state, active, betting_history)

        # Get legal action objects
        action_list = self._get_action_list(round_state, legal_actions)

        if not action_list:
            # Fallback: return a safe action
            if CheckAction in legal_actions:
                return CheckAction()
            elif CallAction in legal_actions:
                return CallAction()
            else:
                return FoldAction()

        # Get probabilities for each action from CFR strategy
        action_probs = []
        for i, action in enumerate(action_list):
            prob = self.cfr.get_action_probability(info_set, i)
            action_probs.append(prob)

        # Normalize probabilities (in case they don't sum to 1)
        total_prob = sum(action_probs)
        if total_prob > 0:
            action_probs = [p / total_prob for p in action_probs]
        else:
            # Uniform if no strategy
            action_probs = [1.0 / len(action_list)] * len(action_list)

        # Sample action according to strategy
        action_index = self._sample_action(action_probs)
        return action_list[action_index]

    def _extract_betting_history(self, round_state) -> str:
        '''
        Extracts betting history from round state.

        This is a simplified version - in practice, you might want to
        track the full history through the round_state.previous_state chain.

        Args:
            round_state: Current round state

        Returns:
            String encoding of betting history
        '''
        # Simplified: use pot commitments and street as proxy
        # In a full implementation, you'd traverse previous_state chain
        history = f"s{round_state.street}_p{round_state.pips[0]}_{round_state.pips[1]}"
        return history

    def _get_action_list(self, round_state, legal_actions):
        '''
        Converts legal action types to concrete action objects.

        Args:
            round_state: Current round state
            legal_actions: Set of legal action types

        Returns:
            List of concrete action objects
        '''
        actions = []
        active = round_state.button % 2
        continue_cost = round_state.pips[1 - active] - round_state.pips[active]

        # Discard actions
        if DiscardAction in legal_actions:
            num_cards = len(round_state.hands[active])
            for i in range(num_cards):
                actions.append(DiscardAction(i))

        # Betting actions
        if FoldAction in legal_actions and continue_cost > 0:
            actions.append(FoldAction())
        if CallAction in legal_actions:
            actions.append(CallAction())
        if CheckAction in legal_actions:
            actions.append(CheckAction())
        if RaiseAction in legal_actions:
            min_raise, max_raise = round_state.raise_bounds()
            # Use a few key raise sizes
            pot = sum(round_state.pips)
            sizes = [min_raise]
            pot_sized = min_raise + pot
            if min_raise < pot_sized < max_raise:
                sizes.append(pot_sized)
            if max_raise not in sizes:
                sizes.append(max_raise)
            for size in sorted(set(sizes)):
                actions.append(RaiseAction(size))

        return actions

    def _sample_action(self, probabilities):
        '''
        Samples an action index according to probabilities.

        Args:
            probabilities: List of probabilities for each action

        Returns:
            Index of sampled action
        '''
        r = random.random()
        cumsum = 0.0
        for i, prob in enumerate(probabilities):
            cumsum += prob
            if r <= cumsum:
                return i
        return len(probabilities) - 1
