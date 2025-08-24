import subprocess
import os
import sys

def main():
    """
    This master script launches the Streamlit application for the IRCTC Bot.
    """
    print("--- IRCTC Tatkal Bot Launcher ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script_path = os.path.join(script_dir, "main.py")

    if not os.path.exists(main_script_path):
        print(f"Error: 'main.py' not found at '{main_script_path}'")
        sys.exit(1)

    command = ["streamlit", "run", main_script_path]

    print(f"Executing command: {' '.join(command)}")
    print("The application UI should now open in your web browser.")

    try:
        process = subprocess.Popen(command, cwd=script_dir)
        process.wait()
    except FileNotFoundError:
        print("\nError: 'streamlit' command not found.")
        print("Please ensure Streamlit is installed (`pip install streamlit`) and in your system's PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
