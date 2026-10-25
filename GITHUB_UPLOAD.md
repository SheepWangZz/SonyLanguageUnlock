# 将 SonyLanguageUnlock 上传到 GitHub

建议将源代码放入仓库，把可直接运行的 Windows ZIP 放到 Releases。以下步骤由你执行；本次没有登录账号、创建远程仓库或公开上传文件。

## 准备源代码

解压 `SonyLanguageUnlock-0.3.2-source.zip` 到一个新的空目录。打开解压后的 `SonyLanguageUnlock` 文件夹，应该直接看到 `README.md`、`README.en.md`、`app.py`、`language_tool/`、`tests/`、`licenses/` 和 `.gitignore`。

使用整理好的 source ZIP，不要上传整个相机研究工作区。源代码包已经排除固件 DAT、Sony 字体、机身配置快照、旧构建与依赖缓存。Windows 运行包也不含 Sony 字体，使用者需要自行选择固件包。

## 创建仓库并上传

1. 登录 GitHub，点击右上角 **+ → New repository**。
2. 仓库名称填 `SonyLanguageUnlock`，选择 Public 或 Private。先不要勾选自动创建 README、.gitignore 或 License，避免与本地文件冲突。
3. 点击 **Create repository**，复制页面上的 HTTPS 仓库地址。
4. 在刚才解压的 `SonyLanguageUnlock` 文件夹打开 PowerShell，执行下面的命令。将最后的示例地址替换成自己的仓库地址。

```powershell
git init -b main
git add .
git status --short
git commit -m "Add SonyLanguageUnlock bilingual desktop app"
git remote add origin https://github.com/YOUR_USERNAME/SonyLanguageUnlock.git
git push -u origin main
```

执行提交前看一眼 `git status --short`，应只有项目源码、说明与依赖许可，不应出现固件、字体、私有快照或 `.build`。首次使用 Git 时，如果它要求设置姓名和邮箱，按终端提示设置为你希望出现在提交记录里的信息。登录提示按 Git 的浏览器授权流程完成，不把密码或令牌写进代码。

GitHub 会默认显示中文 `README.md`，顶部 English 链接跳转到 `README.en.md`。程序本身只有一个 EXE，用户可在界面切换语言。

以上流程参考 [GitHub 官方：添加本地代码](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。

## 发布可运行版本

1. 仓库页面进入 **Releases → Draft a new release**。
2. 新建标签 `v0.3.2`，Target 选 `main`，标题填 `SonyLanguageUnlock 0.3.2`。
3. 附件上传 `SonyLanguageUnlock-0.3.2-windows-x64.zip` 和 `release-checksums.json`。不要只上传 EXE，因为它需要同包的 `_internal`。
4. 版本说明写明：中英界面、先检测设备、中文需匹配固件、当前写入只支持 ILCE-7CM2 / 2.01 / J1、完整 GUI 尚未实机复测。
5. 因当前为验证中的版本，勾选 **This is a pre-release**，确认附件齐全后发布；也可以先点 **Save draft** 保存草稿。

GitHub 会自行提供该标签的源码压缩包，无需把 Windows ZIP 提交到源码仓库。[GitHub 官方：管理 Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)。

## 后续更新

修改代码、完成测试后，在项目目录提交并推送：

```powershell
git add .
git status --short
git commit -m "Describe the changes"
git push
```

对新的程序版本使用新的版本号和 Release 标签。保留 `licenses/` 与 `THIRD_PARTY.md`。若要为自有代码指定开源许可，可另行添加 LICENSE；第三方依赖许可仍分别适用。

## English quick guide

Extract the source ZIP into a new folder. Create an empty GitHub repository named `SonyLanguageUnlock`, without generated README, license, or gitignore files. In the extracted source folder, run the commands above after replacing `YOUR_USERNAME`. Review the staged file list before committing. Publish the Windows ZIP and checksums through **Releases → Draft a new release**, tag `v0.3.2`, targeting `main`. Keep the entire Windows ZIP intact, and mark this unlock/write workflow with incomplete hardware validation as a pre-release. Do not publish local camera records or firmware packages.
