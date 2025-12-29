# MIT Pokerbots Engine 2026
MIT Pokerbots engine and skeleton bots in Python, Java, and C++.

This is the implementation of the engine for playing this year's poker variant, where you get 3 hole cards pre-flop, and you choose a card to discard face up after the flop.

## Setup Instructions
Our engine runs in Python, and to make setup as smooth as possible we can make use of [`uv`](https://docs.astral.sh/uv/), a powerful tool which handles package management, virtual environments, etc.

<span style="opacity: 0.57;"><u>__NOTE: We strongly recommend trying out `uv` even if you are already familiar with tools such as `pip` and `pyenv`__</u></span>

To install `uv`, you can use the following:

```bash
#!/bin/bash

# macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh 

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Now, after installing `uv` and cloning the repo, run the following commands inside the repo:

```bash
#!/bin/bash

# Create a virtual environment with any Python version if your choice >=3.8 (omitting the --python flag will use the most recent python version, which is ok)
uv venv --python 3.x.x # e.g. 3.13.3

# Sync the virtual environment with the given project files (pyproject.toml and uv.lock), which basically installs the dependencies:
# - cython 3.2.3 (needed for pkrbot)
# - pkrbot 1.0.4 (custom library used for hand evaluation)
uv sync
```

That's it! There is no need to download the necessary python versions beforehand since `uv` will attempt to find it and install it if necessary.

Now, to finally run the engine, you can use the Python executable inside of the virtual environment (should be at `<PROJECT_DIR>/.venv/bin/python`) and run `engine.py`. To change the bots which are run, see `config.py`.

### C++ Specific Instructions
If you are writing a bot in C++, you should make sure that you have `C++17`, `cmake>=3.8`, and `boost`, a versatile library which we use for stream-oriented network communication.

There are many ways to install C++ and `cmake` on your machine, but ultimately you want to make sure that your versions are high enough with these commands:

```bash
#!/bin/bash

cmake --version   # should be 3.8 or higher

# Check either g++ or clang++ depending on which compiler you are using
g++ --version     # should show something like g++ (GCC) 10.x or newer
clang++ --version # should show something like Apple clang version 10.x or newer
```

Now, to get `boost`, you can use the following:

```bash
#!/bin/bash

sudo apt-get install libboost-all-dev # Linux
brew install boost                    # macOS
vcpkg install boost                   # Windows
```

<span style="opacity: 0.57;">NOTE: For the macOS command to work, you must first install `brew`, with this command: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`. Now brew should work as needed.
</span>


### Java Specific Instructions
If you are writing a bot in Java, you should make sure that you have `Java>=8` installed on your machine. 

If `java -version` fails or shows a version <1.8, install Java using the instructions below. After installing, use `java -version` again to verify successful installation.

#### macOS

The recommended version is with brew:
```bash
brew install --cask temurin
```

It is also possible to download manually from: [Adoptium](https://adoptium.net).

#### Linux
You can simply run the commands below:
```bash
sudo apt update
sudo apt install -y openjdk-17-jdk
```

#### Windows

You can download manually from: [Adoptium](https://adoptium.net), install using the `.msi` installer, and make sure "Add to PATH" is checked.