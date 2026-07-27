# 推送到GitHub仓库 - 详细步骤

## 方法1：在GitHub网页创建仓库（推荐）

### 步骤1：在GitHub上创建新仓库

1. 打开浏览器，访问 https://github.com/new
2. 填写仓库信息：
   - **Repository name**: `locagent-reproduction`
   - **Description**: `LocAgent reproduction environment for SWE-bench evaluation`
   - **可见性**: 选择 Public 或 Private
   - **不要勾选** "Add a README file"（我们已经有了）
   - **不要勾选** ".gitignore"（我们已经有了）
3. 点击 "Create repository"

### 步骤2：连接并推送

创建完成后，GitHub会显示一个页面，选择 "**…or push an existing repository from the command line**"

在本地执行以下命令：

```bash
# 添加远程仓库（替换 YOUR_USERNAME 为你的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/locagent-reproduction.git

# 推送到GitHub
git branch -M main
git push -u origin main
```

---

## 方法2：使用Git命令行（如果gh已安装）

```bash
# 创建GitHub仓库
gh repo create locagent-reproduction --public --source=. --remote=origin --push

# 或创建私有仓库
gh repo create locagent-reproduction --private --source=. --remote=origin --push
```

---

## 方法3：使用SSH密钥（避免每次输入密码）

如果你还没有配置SSH密钥：

```bash
# 生成SSH密钥
ssh-keygen -t ed25519 -C "a61354020@gmail.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到GitHub: Settings -> SSH and GPG keys -> New SSH key
```

然后使用SSH地址：

```bash
git remote add origin git@github.com:YOUR_USERNAME/locagent-reproduction.git
git push -u origin main
```

---

## 已完成的工作

✅ Git仓库已初始化
✅ .gitignore 已创建
✅ 初始提交已完成 (21个文件, 3168行代码)

包含内容：
- LocAgent 完整代码
- 复现代码和脚本
- 论文分析文档
- 评估协议
- 图索引预生成工具

---

## 当前仓库内容

```
.
├── .gitignore
├── LocAgent/                    # LocAgent源代码
├── baselinePrompt.md
├── docs/                        # 文档
│   ├── 00_paper_summary.md
│   ├── 01_reproduction_plan.md
│   ├── 02_locagent_code_reading.md
│   ├── 03_environment_setup.md
│   ├── 04_evaluation_protocol.md
│   └── locagent_reproducibility_solution.md
├── main.tex
├── main_fixed.tex
├── paper/                       # 论文PDF
└── scripts/                     # 工具脚本
    ├── evaluate_localization.py
    ├── git_repo_manager_optimized.py
    ├── prebuild_graph_indexes.py
    ├── prebuild_indexes_interactive.ps1
    ├── quick_verify_available_samples.py
    ├── run_locagent_verified_10.ps1
    ├── run_locagent_verified_3.ps1
    └── run_locagent_verified_quick.ps1
```

---

## 推送后的下一步

推送成功后，你可以：

1. **添加README.md**（可选）
   ```bash
   echo "# LocAgent Reproduction

   This repository contains the reproduction environment for LocAgent paper evaluation.

   ## Quick Start

   1. Prebuild graph indexes:
      \`\`\`bash
      python scripts/prebuild_graph_indexes.py --eval_n_limit 10
      \`\`\`

   2. Run evaluation:
      \`\`\`bash
      powershell -File scripts/run_locagent_verified_10.ps1
      \`\`\`

   ## Documentation

   See \`docs/\` directory for detailed documentation.

   ## Paper

   - [ICLR 2026 Paper Summary](paper/ICLR_2026_Improving_Code_Localizat.md)
   - [Reproduction Plan](docs/01_reproduction_plan.md)
   - [Evaluation Protocol](docs/04_evaluation_protocol.md)
   " > README.md

   git add README.md
   git commit -m "Add README"
   git push
   ```

2. **设置仓库描述**
   在GitHub仓库页面，点击 "About" 旁边的编辑按钮，添加描述和标签。

---

## 需要帮助？

如果遇到问题，请检查：
1. 网络连接是否正常
2. GitHub账号是否有权限
3. 是否正确配置了用户名和邮箱

常见错误：
- `fatal: 'origin' already exists`: 运行 `git remote remove origin` 后重试
- `fatal: repository not found`: 检查仓库地址是否正确
- `Permission denied`: 检查SSH密钥或使用HTTPS + token