# colab-template

> 本文是 [README.md](README.md) 的中文译本。两者有出入时，以英文版为准。

一个在 Google Colab 上做计算的研究项目模版。研究者和编码 Agent 在 GitHub Issue 里提出问题，用实验回答问题，实验过程记在
Pull Request 里。这里没有 spec 流程，没有审批标签，也没有预算账本，唯一的闸门是一个人合并 Pull Request。

它是 [experiment-template](https://github.com/hoshiori-dev/experiment-template)
的轻量版本。需要正式运行记录、预算和受保护路径时用那一个；一个小团队和它的 Agent
想走得快，又希望几个月后还说得清每个结论的依据时，用这一个。

## 研究怎样推进

**问题就是 Issue。** 任何人（包括 Agent）觉得某件事值得做实验，就开一个 Question。Issue
里写清楚问什么、问题从哪里来、什么结果算是回答了。讨论放在它的评论里，推理过程和问题留在一起。Epic
是把相关问题归到一组的 Issue，除此之外没有别的作用。Task 是普通的工程任务：共享库、demo、报告。

**实验就是 Pull Request。** 实验放在 `experiments/<issue>-<slug>/`，第一次推送时就开草稿 Pull
Request。正文是实验当前的摘要。每个大的进展写成一条评论，发出后不再修改，比如第一次跑通、改变了计划的结果、走不通的路、花了一下午才学到的教训。Pull
Request 不是日志，重试和每次运行的状态不往里写。

**发现随代码一起合并。** Pull Request 提交评审之前，学到的每一件事都要放到以后的读者找得到的地方，没人问到的那些也一样：

| 这条发现是关于                     | 它放到                         |
| ---------------------------------- | ------------------------------ |
| 这个实验：答案、证据、怎样重跑     | `experiments/<id>/README.md`   |
| 研究对象本身，超出这一个实验       | `docs/`                        |
| 怎样在这个仓库里干活               | `.agents/knowledge/`，或 skill |

**由人合并。** 合并表示接受这个答案，并关闭对应的问题。否定的答案同样关闭问题。合并之后，由人决定是否发布权重。

## 用到的工具

| 需要                   | 工具                                                                   |
| ---------------------- | ---------------------------------------------------------------------- |
| 计算                   | Google Colab，通过 [Colab CLI](https://github.com/googlecolab/google-colab-cli) |
| 公开数据集             | Hugging Face Hub 数据集，固定到某个 revision                           |
| 私有数据集             | Google Drive，通过 rclone                                              |
| Checkpoint 和会话文件  | 一个私有的 Hugging Face bucket，每次运行一个前缀                       |
| 公开权重               | Hugging Face Hub 模型仓库                                              |
| 私有权重               | Google Drive                                                           |
| 依赖                   | uv：共享库在根 workspace，每个实验有自己的锁文件                       |
| 报告                   | Quarto（HTML，以及通过 Typst 生成的 PDF）                              |
| 命令                   | just                                                                   |

用这个模版建的项目，用到的东西往往比这少。不需要的直接删掉。

`just run <实验> -- <命令>` 把计算和存储连在一起。它创建一台 Colab VM，上传已提交的代码，按锁文件安装实验的依赖，从 Drive
复制实验声明的私有数据，运行命令，运行期间把输出目录同步到 bucket，最后停掉 VM。用同一个运行名再启动一次，就从 bucket
里的文件接着跑。Colab 会话会毫无预警地结束，所以这一点很重要。

## 配置

1. 用这个模版创建仓库，在 dev container 里打开。容器里所有工具都已装好。
2. 在终端里分别登录：
   - `colab sessions` 会给出一个链接，同意后把授权码粘回终端。
   - `gh auth login`
   - `hf auth login`，供你自己在本机使用 Hub。
3. 在 `justfile` 顶部设置 `BUCKET` 和 `DRIVE_ROOT`。
4. 新建一个细粒度的 Hugging Face 令牌，让它只能写这个 bucket 和项目用到的仓库。把 `.env.example` 复制为
   `.env`，填入令牌。Colab VM 拿到的就是这个令牌，所以权限要收窄。
5. 用最小的授权范围为 rclone 授权 Google Drive：`rclone config create gdrive drive scope=drive.file`。在这个范围下
   rclone 只看得到它自己上传的文件，所以私有数据集要用 `just drive-push` 上传，不要从浏览器拖进去。rclone 内置的
   Google client ID 会在 2026 年内停用，所以请[创建自己的 client ID](https://rclone.org/drive/#making-your-own-client-id)，并在命令里加上
   `client_id=... client_secret=...`。
6. 运行 `just init-storage` 和 `just init-labels`。
7. 在仓库设置里允许 merge commit。实验的 Pull Request 用 merge commit 合并，这样实验 README 引用的提交会留在
   `main` 上。

之后打开你的 Agent，告诉它你想弄清楚什么，或者自己开第一个 Question。

## 日常命令

| 你想要                           | 运行                                                         |
| -------------------------------- | ------------------------------------------------------------ |
| 为 12 号 Issue 开一个实验        | `just new 12 label-smoothing`                                |
| 在 Colab 上运行它的一条命令      | `just run 012-label-smoothing -- python train.py`            |
| 用同一个名字续跑或重跑           | `just run 012-label-smoothing --run NAME -- python train.py` |
| 查看一次运行在 bucket 里留下什么 | `just bucket-ls 012-label-smoothing`                         |
| 把一次运行的文件取到 `.local/out/` | `just bucket-pull 012-label-smoothing NAME`                |
| 上传一个私有数据集               | `just drive-push ./data datasets/my-set/v1`                  |
| 检查格式、lint 和锁文件          | `just check`                                                 |
| 发布已合并实验的权重             | `just deliver-hub ...` 或 `just deliver-drive ...`           |

单独运行 `just` 会列出全部命令。

## 仓库布局

```text
AGENTS.md  CLAUDE.md          Agent 最先读的文件
.agents/knowledge/            怎样在这里干活：工作流、Colab 和存储
.agents/skills/               分步的操作流程，有值得保留的才添加
justfile  scripts/            命令和 Colab 启动器
packages/<name>/              共享库（根 uv workspace）
experiments/<NNN-slug>/       一个实验：README、代码、colab.toml、自己的锁文件、results/
template/experiment/          `just new` 复制的起步模版
demos/<name>/                 演示应用
reports/<name>/               Quarto 报告，图表取自 experiments/*/results/
docs/                         超出单个实验的结论
```

一个目录在有内容可放时才出现。

## Agent

`AGENTS.md` 是唯一的入口，Codex、OpenCode 和 Antigravity 都直接读取它，也直接从 `.agents/skills/` 加载 skill。Claude Code
读取 `CLAUDE.md`，这个文件只引入 `AGENTS.md`；它通过 `.claude/skills/` 里的链接找到 skill。仓库不带任何权限表。唯一的框架设置是
`.claude/settings.json`，用来关闭 Claude Code 在提交和 Pull Request 里的署名；其他框架只有 `AGENTS.md` 里的那条规则。

## 局限

- Colab 不是作业调度器。GPU 有时分配失败，空闲的会话会消失。启动器让运行可以续跑，但不排队，也不自动重试。
- 没有任何东西检查 README 里的数字是否来自它引用的那个提交。工作流这样要求，评审的人可以核对。
- `colab drivemount` 在每台新 VM 上都需要有人在浏览器里同意，所以模版不使用它。

## 许可证

[Apache License 2.0](LICENSE)。
