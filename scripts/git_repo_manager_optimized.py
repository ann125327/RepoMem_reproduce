"""
优化版 git_repo_manager.py
支持仓库缓存，避免重复克隆同一个仓库
"""
import logging
import os
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# 全局缓存目录
CACHE_DIR = "playground/cache"

def get_repo_dir_name(repo: str):
    return repo.replace("/", "_")


def get_cached_repo_dir(repo: str) -> str:
    """获取缓存的仓库目录"""
    repo_name = get_repo_dir_name(repo)
    return os.path.join(CACHE_DIR, repo_name)


def setup_cached_repo(repo: str, base_commit: str) -> str:
    """
    使用缓存的仓库，避免重复克隆

    Args:
        repo: 仓库名称（如 "astropy/astropy"）
        base_commit: 基础提交哈希

    Returns:
        仓库目录路径
    """
    cached_dir = get_cached_repo_dir(repo)

    # 如果缓存不存在，克隆到缓存目录
    if not os.path.exists(cached_dir):
        os.makedirs(CACHE_DIR, exist_ok=True)
        logger.info(f"Cloning {repo} to cache directory: {cached_dir}")
        repo_url = f"https://github.com/{repo}.git"
        subprocess.run(
            ["git", "clone", "--no-single-branch", repo_url, cached_dir],
            check=True,
            text=True,
            capture_output=True
        )
        logger.info(f"Repo cloned to cache: {cached_dir}")

    # 创建临时副本（避免多个样本共享同一个工作目录）
    import uuid
    temp_copy = os.path.join("playground", f"temp_{uuid.uuid4()}", get_repo_dir_name(repo))
    os.makedirs(os.path.dirname(temp_copy), exist_ok=True)

    logger.info(f"Copying cached repo to: {temp_copy}")
    shutil.copytree(cached_dir, temp_copy)

    # 切换到指定提交
    checkout_commit(temp_copy, base_commit)

    return temp_copy


def setup_github_repo(repo: str, base_commit: str, base_dir: str = "/tmp/repos") -> str:
    """
    设置 GitHub 仓库（优化版）

    如果 base_dir 是 UUID 格式的临时目录，使用缓存机制
    否则使用原始逻辑
    """
    # 检测是否是 UUID 临时目录
    is_temp_uuid = "playground" in base_dir and len(os.path.basename(base_dir)) == 36

    if is_temp_uuid:
        # 使用缓存机制
        return setup_cached_repo(repo, base_commit)
    else:
        # 使用原始逻辑
        repo_name = get_repo_dir_name(repo)
        repo_url = f"https://github.com/{repo}.git"
        path = f"{base_dir}/{repo_name}"

        logger.info(f"Clone Github repo {repo_url} to {path} and checkout commit {base_commit}")

        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Directory '{path}' was created.")

        maybe_clone(repo_url, path)
        checkout_commit(path, base_commit)
        return path


def maybe_clone(repo_url, repo_dir):
    if not os.path.exists(f"{repo_dir}/.git"):
        logger.info(f"Cloning repo '{repo_url}'")
        result = subprocess.run(
            ["git", "clone", repo_url, repo_dir],
            check=True,
            text=True,
            capture_output=True,
        )

        if result.returncode == 0:
            logger.info(f"Repo '{repo_url}' was cloned to '{repo_dir}'")
        else:
            logger.info(f"Failed to clone repo '{repo_url}' to '{repo_dir}'")
            raise ValueError(f"Failed to clone repo '{repo_url}' to '{repo_dir}'")


def checkout_commit(repo_dir, commit_hash):
    try:
        subprocess.run(
            ["git", "reset", "--hard", commit_hash],
            cwd=repo_dir,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(e.stderr)
        raise e


# 其他函数保持不变...
def pull_latest(repo_dir):
    subprocess.run(
        ["git", "pull"],
        cwd=repo_dir,
        check=True,
        text=True,
        capture_output=True,
    )


def clean_and_reset_state(repo_dir):
    subprocess.run(
        ["git", "clean", "-fd"],
        cwd=repo_dir,
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "reset", "--hard"],
        cwd=repo_dir,
        check=True,
        text=True,
        capture_output=True,
    )