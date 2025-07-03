# About

This tool will daily crawl https://arxiv.org and use LLMs to summarize them.

Try in: https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/

# Features

- Using the free features of GitHub Actions and GitHub Pages, **no server is required**
- Crawling data starts at dawn every day, and using DeepSeek to summarize. This period is during the off-peak discount period of DeepSeek, and it only costs about 0.2 CNY per day.
- Provides a GitHub Pages front-end interface, uses LocalStorage to store **personalized preference** information (such as keywords and authors of interest), and highlights papers that matches the preferences.
- GitHub Pages takes into account the display effects of both the computer and mobile devices, ensuring that papers can be easily reviewed on mobile devices
- Provides **RSS feeds** for all papers and individual categories, allowing users to subscribe and receive updates in their favorite RSS readers

## 特性

- 🚀 **GitHub Actions & Vercel**: 自动化爬取和API部署，无需自建服务器
- 💰 **成本效益**: 使用DeepSeek模型，比OpenAI便宜10倍
- 🔍 **个性化**: 自定义关注的arXiv分类
- 📱 **移动友好**: 响应式设计，完美支持移动设备
- 📡 **RSS API**: 通过Vercel部署的API提供RSS订阅服务

# Screenshots

- Main page. Highlight the interested keywords and authors.

<img src="images/index.png" alt="main-page" width="800">

- Setting page. Set up keywords and authors and store them in your browser.

<img src="images/setting.png" alt="setting-page" width="600">

- Detail page. Show details of the paper you clicked.

<img src="images/details.png" alt="detail-page" width="500">

- Date select. Enable selecting a single date or a date range for filtering papers (**Notice: a large date range will show lots of papers, which may lead your browser to get stuck.**).

<img src="images/single-date.png" alt="single-date" width="300">
<img src="images/range-date.png" alt="range-date" width="300">

- Statistics page (_in developing_). Help you analyze papers. Extract keywords for papers in the day(s) you select. In addition, if you select a range of dates, the keyword trends will be illustrated. (Fortunately, selecting a large range of papers **will not** stuck your browser to be stuck because this page will not show all papers. It may take a few seconds to process the keywords.)

<img src="images/keyword.png" alt="single-date" width="600">
<img src="images/trends.png" alt="range-date" width="600">

# How to use

This repo will daily crawl arXiv papers about **cs.CV, cs.GR, cs.CL and cs.AI**, and use **DeepSeek** to summarize the papers in **Chinese**.
If you wish to crawl other arXiv categories, use other LLMs, or other languages, please follow the instructions.
Otherwise, you can directly use this repo in https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/. Please star it if you like :)

**Instructions:**

1. Fork this repo to your own account
2. Go to: your-own-repo -> Settings -> Secrets and variables -> Actions
3. Go to Secrets. Secrets are encrypted and used for sensitive data
4. Create two repository secrets named `OPENAI_API_KEY` and `OPENAI_BASE_URL`, and input corresponding values.
5. Go to Variables. Variables are shown as plain text and are used for non-sensitive data
6. Create the following repository variables:
   1. `CATEGORIES`: separate the categories with ",", such as "cs.CL, cs.CV"
   2. `LANGUAGE`: such as "Chinese" or "English"
   3. `MODEL_NAME`: such as "deepseek-chat"
   4. `EMAIL`: your email for push to GitHub
   5. `NAME`: your name for push to GitHub
7. Go to your-own-repo -> Actions -> arXiv-daily-ai-enhanced
8. You can manually click **Run workflow** to test if it works well (it may take about one hour). By default, this action will automatically run every day. You can modify it in `.github/workflows/run.yml`
9. Set up GitHub pages: Go to your own repo -> Settings -> Pages. In `Build and deployment`, set `Source="Deploy from a branch"`, `Branch="main", "/(root)"`. Wait for a few minutes, go to https://\<username\>.github.io/daily-arXiv-ai-enhanced/. Please see this [issue](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced/issues/14) for more precise instructions.

# Vercel部署说明

本项目现已支持通过Vercel部署RSS API服务，提供更稳定的RSS订阅体验。

## 部署步骤

1. 在Vercel上注册账号并连接GitHub仓库
2. 导入你fork的daily-arXiv-ai-enhanced仓库
3. 配置环境变量：
   - `DATA_DIR`: 数据目录路径，默认为 `data`
   - `LANGUAGE`: 语言设置，默认为 `Chinese`
4. 点击部署按钮

部署完成后，你可以通过以下API端点访问RSS服务：

- `/feed` - 获取所有分类的RSS源
- `/feed/{cat}` - 获取特定分类的RSS源，如 `/feed/cs.CL`

可选参数：
- `date` - 指定日期，格式为YYYY-MM-DD
- `lang` - 指定语言，默认为Chinese

## API文档

访问 `/api-docs` 端点可获取完整的API文档。

# To-do list

- [x] Feature: Replace markdown with GitHub pages front-end.
- [ ] Bugfix: In the statistics page, the number of papers for a keyword is not correct.
- [ ] Bugfix: In the date picker, the date and week do not correspond.
- [ ] Feature: Extract keywords with DeepSeek.
- [x] Update instructions for fork users about how to use GitHub Pages.
- [x] Feature: 支持通过Vercel部署RSS API服务

# Contributors

Thanks to the following special contributors for this project!!!

<table>
  <tbody>
    <tr>
      <td align="center" valign="top">
        <a href="https://github.com/JianGuanTHU"><img src="https://avatars.githubusercontent.com/u/44895708?v=4" width="100px;" alt="JianGuanTHU"/><br /><sub><b>JianGuanTHU</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/Chi-hong22"><img src="https://avatars.githubusercontent.com/u/75403952?v=4" width="100px;" alt="Chi-hong22"/><br /><sub><b>Chi-hong22</b></sub></a><br />
      </td>
    </tr>
  </tbody>
</table>

# Acknowledgement

We sincerely thank the following individuals and organizations for their promotion and support!!!

<table>
  <tbody>
    <tr>
      <td align="center" valign="top">
        <a href="https://x.com/GitHub_Daily/status/1930610556731318781"><img src="https://pbs.twimg.com/profile_images/1660876795347111937/EIo6fIr4_400x400.jpg" width="100px;" alt="Github_Daily"/><br /><sub><b>Github_Daily</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://x.com/aigclink/status/1930897858963853746"><img src="https://pbs.twimg.com/profile_images/1729450995850027008/gllXr6bh_400x400.jpg" width="100px;" alt="AIGCLINK"/><br /><sub><b>AIGCLINK</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://www.ruanyifeng.com/blog/2025/06/weekly-issue-353.html"><img src="https://avatars.githubusercontent.com/u/905434" width="100px;" alt="阮一峰的网络日志"/><br /><sub><b>阮一峰的网络日志 <br> 科技爱好者周刊（第 353 期）</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://hellogithub.com/periodical/volume/111"><img src="https://github.com/user-attachments/assets/eff6b6dd-0323-40c4-9db6-444a51bbc80a" width="100px;" alt="《HelloGitHub》第 111 期"/><br /><sub><b>《HelloGitHub》月刊 <br> 第 111 期</b></sub></a><br />
      </td>
    </tr>
  </tbody>
</table>

# Star history

[![Star History Chart](https://api.star-history.com/svg?repos=dw-dengwei/daily-arXiv-ai-enhanced&type=Date)](https://www.star-history.com/#dw-dengwei/daily-arXiv-ai-enhanced&Date)
