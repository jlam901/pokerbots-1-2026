'''
CFR Training Script

Trains a CFR bot through self-play iterations.
Supports resumable training with save/load functionality.
'''
import random
import os
import time
import pkrbot
from cfr_core import CFRAlgorithm
from cfr_game_tree import GameTree
from skeleton.states import RoundState, STARTING_STACK, BIG_BLIND, SMALL_BLIND


class CFRTrainer:
    '''
    Manages CFR training through self-play.
    '''

    def __init__(self, save_path: str = "cfr_strategy.pkl", use_cfr_plus: bool = True,
                 max_strategy_bytes: int = 1_000_000_000):
        '''
        Args:
            save_path: Path to save trained strategy
            use_cfr_plus: Whether to use CFR+ (positive regrets only)
        '''
        self.cfr = CFRAlgorithm(use_cfr_plus=use_cfr_plus)
        self.game_tree = GameTree()
        self.save_path = save_path
        self.max_strategy_bytes = max_strategy_bytes
        self.bytes_per_node = None

    def train(self, num_iterations: int = 1000, save_interval: int = 100, train_player: int = 0):
        '''
        Trains the CFR algorithm for a single player.
        The opponent uses a uniform random strategy.

        Args:
            num_iterations: Number of training iterations
            save_interval: Save strategy every N iterations
            train_player: Which player to train (0 or 1, default 0)
        '''
        print(f"Starting CFR training for {num_iterations} iterations...")
        print(f"Training player {train_player} (opponent uses uniform random strategy)")
        print(f"Strategy will be saved to: {self.save_path}")

        last_log = time.time()
        for i in range(num_iterations):
            # HARD KILL SWITCH (prevents OOM): respect CFR's configured MAX_NODES
            if len(self.cfr.nodes) > self.cfr.MAX_NODES:
                print("Node limit reached, stopping training early")
                self.save()
                break

            initial_state = self.game_tree.create_initial_state()

            self.cfr.train_iteration(
                initial_state,
                player=train_player,
                game_tree=self.game_tree
            )


            # Progress updates
            now = time.time()
            if (i + 1) % 10 == 0 or (now - last_log) >= 30:
                elapsed = now - last_log
                print(
                    f"Iteration {i + 1}/{num_iterations} - Nodes: {len(self.cfr.nodes)} - "
                    f"+{elapsed:.1f}s since last update",
                    flush=True
                )
                last_log = now


            # Save periodically
            if (i + 1) % save_interval == 0:
                self.save()
                print(f"Saved strategy at iteration {i + 1}")

        # Final save
        self.save()
        print(f"Training complete! Final strategy saved to {self.save_path}")
        print(f"Total information sets: {len(self.cfr.nodes)}")

    def save(self):
        '''Saves the current CFR strategy.'''
        size = self.cfr.save(self.save_path)
        if size <= self.max_strategy_bytes:
            if len(self.cfr.nodes) > 0:
                self.bytes_per_node = size / max(1, len(self.cfr.nodes))
            return

        # If file is too large, prune and resave.
        if self.bytes_per_node is None or self.bytes_per_node <= 0:
            # Fallback estimate: ~1KB per node
            self.bytes_per_node = 1024.0

        target_nodes = int((self.max_strategy_bytes * 0.95) / self.bytes_per_node)
        target_nodes = max(10_000, target_nodes)
        removed = self.cfr.prune_to_max_nodes(target_nodes)
        print(f"Pruned {removed} nodes to keep strategy under {self.max_strategy_bytes} bytes")
        size = self.cfr.save(self.save_path)
        if len(self.cfr.nodes) > 0:
            self.bytes_per_node = size / max(1, len(self.cfr.nodes))

    def load(self):
        '''Loads a saved CFR strategy.'''
        self.cfr.load(self.save_path)
        print(f"Loaded strategy from {self.save_path}")
        print(f"Loaded {len(self.cfr.nodes)} information sets")
        print(f"Training iteration: {self.cfr.iteration}")


if __name__ == '__main__':
    import sys

    # Parse command line arguments
    num_iterations = 1000
    save_path = "cfr_strategy.pkl"
    resume = False
    train_player = 0  # Train player 0 by default

    if len(sys.argv) > 1:
        num_iterations = int(sys.argv[1])
    if len(sys.argv) > 2:
        save_path = sys.argv[2]
    if len(sys.argv) > 3:
        if sys.argv[3] == "--resume":
            resume = True
        else:
            train_player = int(sys.argv[3])
    if len(sys.argv) > 4 and sys.argv[4] == "--resume":
        resume = True

    trainer = CFRTrainer(save_path=save_path)

    if resume:
        trainer.load()
        print(f"Resuming training from iteration {trainer.cfr.iteration}")

    try:
        trainer.train(
            num_iterations=num_iterations,
            save_interval=100,
            train_player=train_player
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("CRASH — press Enter to exit")
