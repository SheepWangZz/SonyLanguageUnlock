# A7C II 官方固件字体比较

核对日期：2026-10-25。四份固件均从 Sony 官方下载服务器取得（2.01 为用户此前已有的同一官方包）。逐包解码并验证内部型号 `0x20030014` 与版本，然后比较三份文件的完整字节、大小和 SHA-256。

## 结论

| 固件 | 简体 LTT | 繁体 LTT | 图标 TTF | 与 2.01 是否相同 |
|---|---:|---:|---:|---|
| 1.01 | 1,958,432 | 1,150,740 | 619,208 | 三份均不同 |
| 1.02 | 1,958,432 | 1,150,740 | 619,208 | 三份均不同；三份均与 1.01 一致 |
| 2.00 | 2,054,740 | 1,150,740 | 622,344 | 三份完全一致 |
| 2.01 | 2,054,740 | 1,150,740 | 622,344 | 比较基线 |

**不是所有旧版都相同。** 繁体 LTT 在 1.x 和 2.x 中大小相同但内容不同，不能只按文件名和大小判断。核对范围没有包括未取得的出厂 1.00。

2.01 的三份资源与 2.00 相同。但这只证明文件相同，不证明 2.00 的整套服务写入流程已实测，所以设备版本限制仍是日版 J1 / 2.01。其他机型不能借用这些文件。0.3.0 改为必须由用户选择官方固件包，不再内置或分发这些字体。

## 哈希

| 文件 | 1.01 / 1.02 SHA-256 | 2.00 / 2.01 SHA-256 |
|---|---|---|
| `MYingHeiC-GB18030-SJ_wIcon.ltt` | `46a34ce3a891a4b1b260b79071da6b806f7a5c3bfc08be0691fb2d6e13e2e8d2` | `a8afccc2e226d5a519f3698796c2a76a0ad6e163f7e5fc9e35d5e89d58db3276` |
| `MYingHeiC-Big5-SJ_wIcon.ltt` | `265cbfec60e6f71d169d92027e75e0e2f8737afe1b26f9ab2efce4cb6ef9137d` | `25f3afa8008c6d038e5bf61582c06539a70786a2de1c74fe63e73814d468ab9f` |
| `Sony_DI_Icons.ttf` | `e87fd06c1b0145cd8731af395a435531bc185371bc9e4345171f55a2d912521b` | `f4957fda675cad6c118c91297ed53828fbe4ef0ea28bc50ae2db3458bc5341c2` |

机器可读的源包大小、源包哈希、字体哈希和逐字节比较结果：`language_tool/resources/font-comparison.json`。原研究中的本地字体样本不进入 Git 或发行包。

## 字符表与依赖差异

进一步解析了 LTT 中的内嵌 TrueType 字体与独立图标 TTF。下面的“码点数”是字体 Unicode cmap 映射数，不是菜单实际使用的汉字数：

| 资源 | 1.01 / 1.02 字形数；码点数 | 2.00 / 2.01 字形数；码点数 | 变化 |
|---|---|---|---|
| 简体内嵌字体 | 33,967；28,558 | 34,229；28,825 | 新增 268 个码点、移除 1 个，净增 267 |
| 繁体内嵌字体 | 17,709；13,572 | 17,709；13,572 | 内嵌 sfnt 完全一致，变化在 LTT 容器 |
| 图标 TTF | 1,731；1,683 | 1,742；1,693 | 新增 10 个私用区码点，字形总数增 11 |

新增图标码点为 `U+E6AF` 至 `U+E6B7`，以及 `U+E6B9`。简体新增码点中包括控制字符和非汉字，不能把 268 说成新增 268 个汉字。完整列表与字体表哈希见 `language_tool/resources/font-characters.json`。

四版两份中文 LTT 均声明 `Sony_DI_Icons.ttf`、`targetdirectory=.`。因此，**外部图标依赖至少在已取得的 1.01 就存在，并不是 2.00 才新增**。这并不证明每台 1.01 机身都缺少该文件，也不能代替旧版实机菜单测试。

## 可追溯来源

- [Sony 1.01 原始安装包](https://support.d-imaging.sony.co.jp/download/NEX/OUcm2ZA4wE/BODYDATA.DAT?fm=am)，来自 [2023-10-28 的官方页面存档](https://web.archive.org/web/20231028151927/https://www.sony.com/electronics/support/e-mount-body-ilce-7-series/ilce-7cm2/software/00301105)。
- [Sony 1.02 原始安装包](https://support.d-imaging.sony.co.jp/download/NEX/7cm2kgTyEu/BODYDATA.DAT?fm=am)，来自 [2024-03-29 的官方页面存档](https://web.archive.org/web/20240329114140/https://www.sony.com/electronics/support/e-mount-body-ilce-7-series/ilce-7cm2/software/00301105)。
- [Sony 2.00 原始安装包](https://support.d-imaging.sony.co.jp/download/NEX/jL801e5ec9/BODYDATA.DAT?fm=am)，来自 [2025-10-15 的官方页面存档](https://web.archive.org/web/20251015064441/https://www.sony.com/electronics/support/software/00301105)。
- [Sony 2.01 原始安装包](https://support.d-imaging.sony.co.jp/download/NEX/uua3b90658/BODYDATA.DAT?fm=jp)，[Sony 官方版本历史](https://support.d-imaging.sony.co.jp/www/cscs/firm/?area=jp&lang=jp&mdl=ILCE-7CM2)。

字体变化的版本边界与“哪版起中文需要补文件”不是同一个问题。后者还需要机身地区、机身文件是否存在、字体映射、删除逻辑及实际 UI 测试。本次界面改版不会扩大机型或固件写入范围。
