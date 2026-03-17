#!/bin/sh
# Cross-platform Python script runner for Agent Skills
# Usage: ./scripts/run.sh <path-to-script.py> [args...]

set -e

find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            version=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
            if [ "$version" = "3" ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

install_guide() {
    echo ""
    echo "ERROR: Python 3 is not installed."
    echo ""
    echo "Install Python 3 using one of the following methods:"
    echo ""

    case "$(uname -s)" in
        Linux*)
            if command -v apt >/dev/null 2>&1; then
                echo "  sudo apt install python3"
            elif command -v zypper >/dev/null 2>&1; then
                echo "  sudo zypper install python3"
            elif command -v dnf >/dev/null 2>&1; then
                echo "  sudo dnf install python3"
            elif command -v yum >/dev/null 2>&1; then
                echo "  sudo yum install python3"
            elif command -v pacman >/dev/null 2>&1; then
                echo "  sudo pacman -S python"
            else
                echo "  Install python3 using your distribution's package manager."
            fi
            ;;
        Darwin*)
            echo "  brew install python3"
            echo ""
            echo "  If Homebrew is not installed:"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            ;;
        *)
            echo "  Download from https://www.python.org/downloads/"
            ;;
    esac

    echo ""
    echo "After installation, re-run this script."
    exit 1
}

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path-to-script.py> [args...]"
    echo ""
    echo "Example:"
    echo "  $0 git-workflow/scripts/validate_commit_msg.py --help"
    exit 1
fi

PYTHON=$(find_python) || install_guide

exec "$PYTHON" "$@"
