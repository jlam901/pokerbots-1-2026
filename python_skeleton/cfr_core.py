'''
Core Counterfactual Regret Minimization (CFR) Algorithm

Implements:
- Regret matching for strategy updates
- Strategy averaging for final policy
- CFR+ variant (positive regret only)
'''
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import pickle
import os

from cfr_info_set import InformationSet


class CFRNode:
    '''
    Represents a node in the CFR game tree, storing regrets and strategies.
    '''

    def __init__(self, info_set: InformationSet, num_actions: int):
        '''
        Args:
            info_set: The information set this node represents
            num_actions: Number of legal actions at this node
        '''
        self.info_set = info_set
        self.num_actions = num_actions

        # Regret values for each action
        # Using defaultdict to handle new actions gracefully
        self.regret_sum = defaultdict(float)

        # Strategy sum for averaging (used for final policy)
        self.strategy_sum = defaultdict(float)

        # Current strategy (computed from regrets)
        self.strategy = None

        # Reach probability sum (for weighted strategy averaging)
        self.reach_prob_sum = 0.0

    def get_strategy(self, reach_prob: float) -> Dict[int, float]:
        '''
        Computes current strategy using regret matching.

        Args:
            reach_prob: Probability of reaching this node

        Returns:
            Dictionary mapping action indices to probabilities
        '''
        # Normalize regrets (CFR+ uses positive regrets only)
        normalizing_sum = 0.0
        strategy = {}

        for action in range(self.num_actions):
            # CFR+: only use positive regrets
            regret = max(0.0, self.regret_sum[action])
            strategy[action] = regret
            normalizing_sum += regret

        # Normalize to probabilities
        if normalizing_sum > 0:
            for action in strategy:
                strategy[action] /= normalizing_sum
        else:
            # Uniform strategy if no positive regrets
            for action in range(self.num_actions):
                strategy[action] = 1.0 / self.num_actions

        # Update strategy sum for averaging
        self.reach_prob_sum += reach_prob
        for action in range(self.num_actions):
            self.strategy_sum[action] += reach_prob * strategy[action]

        self.strategy = strategy
        return strategy

    def get_average_strategy(self) -> Dict[int, float]:
        '''
        Returns the average strategy (used for final policy).

        Returns:
            Dictionary mapping action indices to probabilities
        '''
        normalizing_sum = sum(self.strategy_sum.values())

        if normalizing_sum > 0:
            avg_strategy = {}
            for action in range(self.num_actions):
                avg_strategy[action] = self.strategy_sum[action] / normalizing_sum
            return avg_strategy
        else:
            # Uniform if no training
            avg_strategy = {}
            for action in range(self.num_actions):
                avg_strategy[action] = 1.0 / self.num_actions
            return avg_strategy

    def update_regret(self, action: int, regret: float):
        '''
        Updates regret for a specific action.

        Args:
            action: Action index
            regret: Counterfactual regret value to add
        '''
        self.regret_sum[action] += regret


class CFRAlgorithm:
    '''
    Main CFR algorithm implementation.
    '''

    def __init__(self, use_cfr_plus: bool = True):
        '''
        Args:
            use_cfr_plus: If True, use CFR+ (only positive regrets)
        '''
        self.use_cfr_plus = use_cfr_plus

        # Map from information set keys to CFR nodes
        self.nodes: Dict[str, CFRNode] = {}

        # Training iteration counter
        self.iteration = 0

        # MAX_NODES: Memory headroom is mainly needed for training.
        # During gameplay (inference), memory usage is much lower.
        # If no other processes are running, you can increase this to use more RAM.
        # Rough estimate: each node uses ~1-2KB, so 2M nodes ≈ 2-4GB RAM during training.
        # Set higher if you have more RAM available and no other processes running.
        self.MAX_NODES = 3_000_000
        # Set to True once we hit MAX_NODES; used to avoid crashing and keep training on existing nodes
        self.node_cap_reached = False

    def get_node(self, info_set: InformationSet, num_actions: int) -> Optional[CFRNode]:
        '''
        Gets or creates a CFR node for an information set.

        Args:
            info_set: The information set
            num_actions: Number of legal actions

        Returns:
            CFRNode for this information set
        '''
        if info_set.key not in self.nodes:
            if len(self.nodes) >= self.MAX_NODES:
                # Don't crash; mark and refuse to create new nodes
                self.node_cap_reached = True
                return None
            self.nodes[info_set.key] = CFRNode(info_set, num_actions)
        else:
            # If node exists but num_actions doesn't match, update it to the larger value
            # This handles cases where the same info set can have different action counts
            # (e.g., different number of cards to discard)
            existing_node = self.nodes[info_set.key]
            if existing_node.num_actions < num_actions:
                # Expand the node to handle more actions
                # Initialize new action regrets/strategy sums to 0
                for i in range(existing_node.num_actions, num_actions):
                    existing_node.regret_sum[i] = 0.0
                    existing_node.strategy_sum[i] = 0.0
                existing_node.num_actions = num_actions
        return self.nodes[info_set.key]

    def cfr(self,
            round_state,
            player: int,
            reach_probs: Tuple[float, float],
            betting_history: str = "",
            game_tree=None,
            depth: int=0) -> float:
        '''
        Counterfactual Regret Minimization recursive algorithm.

        This is the core CFR algorithm that traverses the game tree,
        computes counterfactual values, and updates regrets.

        Args:
            round_state: Current game state
            player: Player index (0 or 1)
            reach_probs: (reach_prob_player0, reach_prob_player1)
            betting_history: String encoding betting actions
            game_tree: GameTree instance for getting legal actions
            depth: Current depth in the game tree (for debugging)

        Returns:
            Expected utility for the given player
        '''
        from skeleton.states import TerminalState
        from skeleton.actions import DiscardAction

        MAX_DEPTH = 100

        if depth > MAX_DEPTH:
            return 0.0


        # SAFETY: abort if state is not progressing
        if hasattr(round_state, "street"):
            if round_state.street > 5:
                return 0.0

        # Handle TrainingRoundState wrapper
        actual_state = round_state
        if hasattr(round_state, 'round_state'):
            actual_state = round_state.round_state

        # Terminal node: return utility
        if isinstance(actual_state, TerminalState):
            return actual_state.deltas[player]

        # Use actual_state for logic
        state_for_logic = actual_state

        MAX_ACTIONS_PER_ROUND = 6

        if betting_history.count("r") > MAX_ACTIONS_PER_ROUND:
            # Force terminal utility approximation
            from skeleton.states import TerminalState
            if hasattr(round_state, "deltas"):
                return actual_state.deltas[player]
            return 0.0


        from skeleton.actions import RaiseAction, FoldAction, CallAction, CheckAction, DiscardAction

        raw_actions = actual_state.legal_actions()
        legal_actions = []

        active = state_for_logic.button % 2

        for action in raw_actions:
            if action is RaiseAction:
                # Trim raise abstraction to only min-raise and max-raise (all-in)
                min_raise, max_raise = actual_state.raise_bounds()
                sizes = [min_raise]
                if max_raise != min_raise:
                    sizes.append(max_raise)

                for size in sorted(set(sizes)):
                    legal_actions.append(RaiseAction(size))
            elif action is DiscardAction:
                # Create DiscardAction instances for each card in hand
                num_cards = len(actual_state.hands[active])
                for i in range(num_cards):
                    legal_actions.append(DiscardAction(i))
            elif action is FoldAction:
                legal_actions.append(FoldAction())
            elif action is CallAction:
                legal_actions.append(CallAction())
            elif action is CheckAction:
                legal_actions.append(CheckAction())




        # Player decision node
        if active == player:
            # This is our decision node
            from cfr_info_set import create_info_set_from_state

            info_set = create_info_set_from_state(state_for_logic, player, betting_history)
            num_actions = len(legal_actions)
            node = self.get_node(info_set, num_actions)
            if node is None:
                # Node cap reached and this info set wasn't previously seen.
                # Return a neutral approximation so training continues on existing nodes.
                return 0.0

            # Get strategy for this information set
            strategy = node.get_strategy(reach_probs[player])

            # Compute counterfactual value for each action
            action_utils = {}

            # Use uniform probability as default if strategy doesn't have this action index
            uniform_prob = 1.0 / num_actions

            for i, action in enumerate(legal_actions):
                # Get strategy probability for this action, defaulting to uniform if not found
                action_prob = strategy.get(i, uniform_prob)

                # Compute new reach probabilities
                new_reach_probs = (
                    reach_probs[0] * (action_prob if active == 0 else 1.0),
                    reach_probs[1] * (action_prob if active == 1 else 1.0)
                )

                # Update betting history
                new_history = betting_history + self._action_to_string(action, state_for_logic)

                # Recursive call
                next_state = actual_state.proceed(action)

                action_utils[i] = self.cfr(next_state, player, new_reach_probs, new_history, game_tree, depth+1)

            # Compute node utility (weighted average)
            node_util = sum(strategy.get(i, uniform_prob) * action_utils[i] for i in range(len(legal_actions)))

            # Update regrets
            for i in range(len(legal_actions)):
                # Counterfactual regret = (action utility - node utility) * opponent reach prob
                regret = (action_utils[i] - node_util) * reach_probs[1 - player]
                node.update_regret(i, regret)

            return node_util

        else:
            # Opponent's decision node - sample according to their strategy
            from cfr_info_set import create_info_set_from_state

            info_set = create_info_set_from_state(state_for_logic, active, betting_history)
            num_actions = len(legal_actions)

            # Get opponent's strategy
            strategy = {i: 1.0 / num_actions for i in range(num_actions)}

            # Sample action according to strategy (use expected value)
            action_utils = {}
            for i, action in enumerate(legal_actions):
                action_prob = strategy.get(i, 1.0 / num_actions)
                new_reach_probs = (
                    reach_probs[0] * (action_prob if active == 0 else 1.0),
                    reach_probs[1] * (action_prob if active == 1 else 1.0)
                )

                new_history = betting_history + self._action_to_string(action, state_for_logic)
                next_state = actual_state.proceed(action)

                action_utils[i] = self.cfr(next_state, player, new_reach_probs, new_history, game_tree, depth+1)

            # Return expected value
            return sum(strategy.get(i, 1.0 / num_actions) * action_utils[i]
                      for i in range(len(legal_actions)))

    def _action_to_string(self, action, state) -> str:
        '''
        Converts an action to a string for betting history.

        Args:
            action: The action object
            round_state: Current round state

        Returns:
            String representation of the action
        '''
        from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction

        if isinstance(action, FoldAction):
            return "f"
        elif isinstance(action, CallAction):
            return "c"
        elif isinstance(action, CheckAction):
            return "k"
        elif isinstance(action, RaiseAction):
            return f"r{action.amount}"
        elif isinstance(action, DiscardAction):
            return f"d{action.card}"
        return ""

    def train_iteration(self, round_state, player: int, game_tree=None):
        '''
        Performs one iteration of CFR training.

        Args:
            round_state: Initial game state
            player: Player index to train for
            game_tree: Optional GameTree instance
        '''
        reach_probs = (1.0, 1.0)
        self.cfr(round_state, player, reach_probs, "", game_tree)
        self.iteration += 1

    def get_action_probability(self, info_set: InformationSet, action_index: int) -> float:
        '''
        Gets the probability of taking an action from an information set.
        Uses average strategy for final policy.

        Args:
            info_set: The information set
            action_index: Index of the action

        Returns:
            Probability of taking this action
        '''
        if info_set.key not in self.nodes:
            # No training data - return uniform
            return 1.0 / 3  # Rough estimate

        node = self.nodes[info_set.key]
        avg_strategy = node.get_average_strategy()
        return avg_strategy.get(action_index, 1.0 / node.num_actions)

    def save(self, filepath: str):
        '''
        Saves the CFR algorithm state to disk.

        Args:
            filepath: Path to save file
        '''
        data = {
            'nodes': self.nodes,
            'iteration': self.iteration,
            'use_cfr_plus': self.use_cfr_plus
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        return os.path.getsize(filepath)

    def prune_to_max_nodes(self, max_nodes: int):
        '''
        Prunes least-visited nodes to fit under a maximum node count.

        Uses reach_prob_sum as a proxy for node importance.
        '''
        if len(self.nodes) <= max_nodes:
            return 0

        items = list(self.nodes.items())
        # Sort by reach probability sum (ascending).
        items.sort(key=lambda kv: kv[1].reach_prob_sum)
        to_remove = len(items) - max_nodes
        for i in range(to_remove):
            del self.nodes[items[i][0]]
        return to_remove

    def load(self, filepath: str):
        '''
        Loads the CFR algorithm state from disk.

        Args:
            filepath: Path to load file
        '''
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.nodes = data['nodes']
                self.iteration = data.get('iteration', 0)
                self.use_cfr_plus = data.get('use_cfr_plus', True)
