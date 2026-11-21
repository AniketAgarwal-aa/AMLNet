"""Hugging Face Publication Utility for AMLNet 2.0 Research Artifacts.

Safely uploads verified model checkpoints, manifests, and documentation
to Hugging Face Hub (target: AniketAgarwal-aa/AMLNet-Research).
"""
import os
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Upload AMLNet 2.0 release package to Hugging Face Hub.")
    parser.add_argument("--repo-id", default="AniketAgarwal-aa/AMLNet-Research", help="Target repository ID")
    parser.add_argument("--pkg-dir", default="dist_hf", help="Local directory containing prepared release package")
    parser.add_argument("--private", action="store_true", help="Set repository to private if creating")
    args = parser.parse_args()

    pkg_path = Path(args.pkg_dir)
    if not pkg_path.exists():
        print(f"Error: Package directory '{args.pkg_dir}' does not exist.")
        sys.exit(1)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("Error: huggingface_hub is not installed in the environment.")
        sys.exit(1)

    api = HfApi()

    print(f"Connecting to Hugging Face Hub...")
    try:
        user_info = api.whoami()
        print(f"Authenticated as: {user_info.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Authentication / Network Error: {e}")
        print("Ensure you have a valid token (huggingface-cli login) and network connectivity.")
        sys.exit(1)

    print(f"Verifying repository: {args.repo_id}")
    try:
        repo_info = api.repo_info(repo_id=args.repo_id, repo_type="model")
        print(f"Repository exists. Private={repo_info.private}")
    except Exception:
        print(f"Repository {args.repo_id} does not exist yet. Creating...")
        api.create_repo(repo_id=args.repo_id, repo_type="model", private=args.private, exist_ok=True)
        print("Repository created successfully.")

    print(f"Uploading files from '{pkg_path}' to '{args.repo_id}'...")
    api.upload_folder(
        folder_path=str(pkg_path),
        repo_id=args.repo_id,
        repo_type="model",
        commit_message="Release AMLNet 2.0 model checkpoints and 5-tier benchmark manifests"
    )
    print(f"Upload complete! Available at: https://huggingface.co/{args.repo_id}")

if __name__ == "__main__":
    main()
