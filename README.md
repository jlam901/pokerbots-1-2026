# pokerbots-1-2026
As a heads-up, you can edit the code and commit changes without installing/running a virtual environment. If you do want to test out the pokerbot though (locally not through the scrimmage server), you need to install a virtual environment and run it in there.


# Setup Instructions
Our engine runs in Python, and to make setup as smooth as possible we can make use of uv, a powerful tool which handles package management, virtual environments, etc.

NOTE: We strongly recommend trying out uv even if you are already familiar with tools such as pip and pyenv

To install uv, you can use the following:

# macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh 

# Windows (INSTALL WINDOWS SUBSYSTEM FOR LINUX, I USED UBUNTU)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"


Now, after installing uv and cloning the repo, run the following commands inside the repo:

# Create a virtual environment with a recent Python version chosen by uv
uv venv

Optional: you can also use any Python version of your choice >=3.8, using e.g. `uv venv --python 3.13.3`

# Sync the virtual environment with the given project files (pyproject.toml and uv.lock), which basically installs the dependencies:
- cython 3.2.3 (needed for pkrbot)
- pkrbot 1.0.4 (custom library used for hand evaluation)
use:
uv sync

That's it! There is no need to download the necessary python versions beforehand since uv will attempt to find it and install it if necessary.

Now, to finally run the engine, you can use the Python executable inside of the virtual environment (should be at <PROJECT_DIR>/.venv/bin/python) and run engine.py. To change the bots which are run, see config.py.
