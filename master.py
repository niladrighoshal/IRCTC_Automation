import subprocess
import os
import sys

def main():
    """
    This master script launches the Streamlit application for the IRCTC Bot.
    It ensures that the command is run from the script's directory and
    provides a simple, single point of entry.
    """
    print("--- IRCTC Tatkal Bot Launcher ---")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script_path = os.path.join(script_dir, "main.py")

    if not os.path.exists(main_script_path):
        print(f"Error: 'main.py' not found at '{main_script_path}'")
        sys.exit(1)

    # The command to run the Streamlit app
    command = ["streamlit", "run", main_script_path]

    print(f"Executing command: {' '.join(command)}")
    print("The application UI should now open in your web browser.")
    print("You can close this console window to stop the application.")

    try:
        # We use Popen to launch the process without blocking this script,
        # though for this simple launcher, run with check=True would also work.
        process = subprocess.Popen(command, cwd=script_dir)
        process.wait() # Wait for the process to complete (i.e., user closes Streamlit)
    except FileNotFoundError:
        print("\nError: 'streamlit' command not found.")
        print("Please ensure Streamlit is installed (`pip install streamlit`) and in your system's PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
