"""Explicit optional hosted deployment; never requests a hardware upgrade."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
from huggingface_hub import HfApi

ROOT=Path(__file__).resolve().parents[1]
USER='F4K3S4T1SH'

def main():
    parser=argparse.ArgumentParser(description='Publish reviewed source to a Docker Space. A paid plan may be required by Hugging Face; this script never buys one.')
    parser.add_argument('--publish',action='store_true',help='Actually create/update the Space')
    args=parser.parse_args()
    if not args.publish:
        print('Prepared for '+USER+'/geoai-outdoor-assistant. Not published. Use --publish only after selecting this hosting option.')
        return
    api=HfApi()
    if api.whoami()['name'].lower()!=USER.lower(): raise RuntimeError('Wrong Hugging Face account')
    repo=USER+'/geoai-outdoor-assistant'
    api.create_repo(repo,repo_type='space',space_sdk='docker',private=False,exist_ok=True)
    with TemporaryDirectory() as tmp:
        dest=Path(tmp)
        for name in ('Dockerfile','requirements.txt','LICENSE'):
            shutil.copy2(ROOT/name,dest/name)
        for name in ('geoai','deployment'):
            shutil.copytree(ROOT/name,dest/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copy2(ROOT/'deployment/SPACE_README.md',dest/'README.md')
        shutil.copy2(ROOT/'README.md',dest/'PROJECT_README.md')
        api.upload_folder(repo_id=repo,repo_type='space',folder_path=dest,commit_message='Deploy GeoAI CPU assistant')
    print('Uploaded https://huggingface.co/spaces/'+repo+'; build and runtime still require verification.')

if __name__=='__main__': main()
