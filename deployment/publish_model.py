"""Publish only the reviewed model card and configuration after local HF login."""
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd

ROOT=Path(__file__).resolve().parents[1]
USER='F4K3S4T1SH'
REPO=USER+'/geoai-outdoor-model'

def main():
    api=HfApi()
    who=api.whoami()['name']
    if who.lower()!=USER.lower(): raise RuntimeError('Please sign in as '+USER)
    api.create_repo(REPO,repo_type='model',private=False,exist_ok=True)
    api.create_commit(REPO,commit_message='Add GeoAI model configuration and upstream attribution',operations=[
        CommitOperationAdd(path_in_repo='README.md',path_or_fileobj=str(ROOT/'submission/model-card.md')),
        CommitOperationAdd(path_in_repo='runtime_config.json',path_or_fileobj=str(ROOT/'submission/runtime_config.json'))])
    print('Published https://huggingface.co/'+REPO)

if __name__=='__main__': main()
