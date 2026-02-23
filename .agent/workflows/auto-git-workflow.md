---
description: Auto Git Commit and Push Workflow
---

當你完成了一個階段的程式碼開發，或者使用者要求你 Commit 和 Push 時，請嚴格執行以下流程：

1. **檢查並更新 `README.md`**：
   - 根據你剛剛修改或新增的程式碼，檢視現有的 `README.md` 內容。
   - 評估是否需要更新文件（例如：新增了指令、改變了環境變數、添加了新功能說明）。
   - **注意**：請針對相關段落進行修改與重寫，**絕對不要**只是盲目地把新資訊 append (附加) 在文件最下方。

2. **檢查並更新 `.gitignore`**： 
   - 檢查專案中是否有因為這次改動而產生的新追蹤外檔案（例如：暫存資料、日誌、新的設定檔或本機資料庫）。
   - 如果有，請將它們加入到 `.gitignore` 中，確保不會污染 Git 儲存庫。

3. **執行 Git Commit**：
   - 根據剛剛的修改，構思一段清楚的 commit message。
   // turbo
   - 使用 `run_command` 執行 `git add .` 與 `git commit -m "<提交訊息>"`。

4. **執行 Git Push**：
   // turbo
   - 使用 `run_command` 執行 `git push` 將進度推送到遠端。

5. **回報使用者**：
   - 告知使用者 README 與 .gitignore 已檢查/更新完畢，且所有變更均已成功 Commit 和 Push。