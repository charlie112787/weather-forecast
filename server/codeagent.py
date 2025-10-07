import tkinter as tk
from tkinter import scrolledtext, font, messagebox
import json
import os
import subprocess
import urllib.request
import threading
import re
import sys 

class CodeAgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Agent - Ollama 驅動執行")
        self.root.configure(bg="#2E2E2E")
        self.created_files = []

        # --- 樣式設定 ---
        self.font_main = font.Font(family="Consolas", size=11)
        self.font_bold = font.Font(family="Arial", size=12, weight="bold")
        
        # --- 視窗大小與置中 ---
        self.center_window(900, 800)

        # --- 主框架 ---
        main_frame = tk.Frame(self.root, bg="#2E2E2E", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)

        # --- Ollama 設定 ---
        settings_frame = tk.Frame(main_frame, bg="#2E2E2E")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        settings_frame.columnconfigure(1, weight=1)

        tk.Label(settings_frame, text="Ollama API URL:", font=self.font_bold, fg="#FFFFFF", bg="#2E2E2E").grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.ollama_url_entry = tk.Entry(settings_frame, font=self.font_main, bg="#1E1E1E", fg="#D4D4D4", insertbackground="#FFFFFF", relief=tk.FLAT, width=40)
        self.ollama_url_entry.grid(row=0, column=1, sticky="ew")
        self.ollama_url_entry.insert(0, "http://localhost:11444/api/generate")

        tk.Label(settings_frame, text="Ollama 模型:", font=self.font_bold, fg="#FFFFFF", bg="#2E2E2E").grid(row=1, column=0, padx=(0, 10), pady=(5,0), sticky="w")
        self.ollama_model_entry = tk.Entry(settings_frame, font=self.font_main, bg="#1E1E1E", fg="#D4D4D4", insertbackground="#FFFFFF", relief=tk.FLAT, width=40)
        self.ollama_model_entry.grid(row=1, column=1, sticky="ew", pady=(5,0))
        self.ollama_model_entry.insert(0, "llama3")

        # --- 輸入區域 ---
        tk.Label(main_frame, text="在此貼上 AI 的完整回應或專案路徑圖:", font=self.font_bold, fg="#FFFFFF", bg="#2E2E2E").grid(row=1, column=0, columnspan=2, pady=(10, 5), sticky="w")
        self.input_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10, font=self.font_main, bg="#1E1E1E", fg="#D4D4D4", insertbackground="#FFFFFF", relief=tk.FLAT)
        self.input_text.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.input_text.focus()

        # --- 選項框架 (按鈕與核取方塊) ---
        options_frame = tk.Frame(main_frame, bg="#2E2E2E")
        options_frame.grid(row=3, column=0, columnspan=2, pady=15, sticky="ew")
        options_frame.columnconfigure(0, weight=1) 
        options_frame.columnconfigure(4, weight=1)

        self.show_all_button = tk.Button(options_frame, text="Show All Code", font=self.font_bold, bg="#3A7D7D", fg="#FFFFFF", relief=tk.FLAT, command=self.start_show_all_thread, padx=10, pady=5)
        self.show_all_button.grid(row=0, column=1, padx=(0, 5))

        self.show_files_button = tk.Button(options_frame, text="Show Created Files", font=self.font_bold, bg="#4A90E2", fg="#FFFFFF", relief=tk.FLAT, command=self.show_created_files, padx=10, pady=5, state=tk.DISABLED)
        self.show_files_button.grid(row=0, column=2, padx=(0, 5))

        self.process_button = tk.Button(options_frame, text="Generate and Execute Plan", font=self.font_bold, bg="#007ACC", fg="#FFFFFF", relief=tk.FLAT, command=self.start_processing_thread, padx=10, pady=5)
        self.process_button.grid(row=0, column=3, padx=(5, 0))

        self.show_details_var = tk.BooleanVar(value=True)
        details_check = tk.Checkbutton(options_frame, text="Show detailed logs", variable=self.show_details_var, font=self.font_main, fg="#CCCCCC", bg="#2E2E2E", selectcolor="#1E1E1E", activebackground="#2E2E2E", activeforeground="#FFFFFF")
        details_check.grid(row=0, column=5, sticky="e", padx=10)


        # --- 輸出區域 ---
        tk.Label(main_frame, text="執行結果:", font=self.font_bold, fg="#FFFFFF", bg="#2E2E2E").grid(row=4, column=0, columnspan=2, pady=(5, 5), sticky="w")
        self.output_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, font=self.font_main, bg="#1E1E1E", fg="#D4D4D4", relief=tk.FLAT)
        self.output_text.config(state=tk.DISABLED)
        self.output_text.grid(row=5, column=0, columnspan=2, sticky="nsew")
        
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(5, weight=2)

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def center_window_toplevel(self, toplevel, width, height):
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()

        x = main_x + (main_width // 2) - (width // 2)
        y = main_y + (main_height // 2) - (height // 2)
        toplevel.geometry(f'{width}x{height}+{x}+{y}')

    def log_output(self, message):
        self.root.after(0, self._insert_output, message)

    def _insert_output(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def start_processing_thread(self):
        self.created_files = []
        self.process_button.config(state=tk.DISABLED, text="處理中...")
        self.show_all_button.config(state=tk.DISABLED)
        self.show_files_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.generate_and_execute_plan)
        thread.daemon = True
        thread.start()
        
    def start_show_all_thread(self):
        self.created_files = []
        self.process_button.config(state=tk.DISABLED)
        self.show_all_button.config(state=tk.DISABLED, text="掃描中...")
        self.show_files_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.create_source_code_bundle)
        thread.daemon = True
        thread.start()

    def is_path_map(self, content):
        tree_chars = ['├──', '└──', '│']
        if any(char in content for char in tree_chars):
            return True
        if len(re.findall(r'/\s*$', content, re.MULTILINE)) > 1:
            return True
        return False

    def create_structure_from_map(self, path_map_text):
        self.log_output("🔍 偵測到輸入為路徑圖，開始建立檔案結構...\n")
        files_created = 0
        dirs_created = 0
        path_stack = []
        lines = path_map_text.strip().split('\n')

        for line in lines:
            if not line.strip():
                continue
            cleaned_line = re.sub(r'^[│├└─\s]*', '', line)
            prefix = line[:len(line) - len(line.lstrip(' │├└─'))]
            level = len(prefix.replace('├──', '   ').replace('└──', '   ').replace('│', ' ').replace('   ', '    ')) // 4
            item_name = cleaned_line.strip()
            
            while len(path_stack) > level:
                path_stack.pop()
            current_path_base = os.path.join(*path_stack) if path_stack else ''
            is_dir = item_name.endswith(('/', '\\'))
            item_name_no_slash = item_name.rstrip('/\\')
            full_path = os.path.join(current_path_base, item_name_no_slash)

            try:
                if is_dir:
                    os.makedirs(full_path, exist_ok=True)
                    self.log_output(f"📁 已建立資料夾: {full_path}\n")
                    dirs_created += 1
                    path_stack.append(item_name_no_slash)
                else:
                    parent_dir = os.path.dirname(full_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        pass
                    self.log_output(f"📄 已建立檔案: {full_path}\n")
                    self.created_files.append({'path': full_path, 'content': ''})
                    files_created += 1
            except Exception as e:
                self.log_output(f"❌ 建立 '{full_path}' 時發生錯誤: {e}\n")

        self.log_output(f"\n--- ✨ 結構建立完成！ ---\n")
        self.log_output(f"✅ 總共建立了 {dirs_created} 個資料夾和 {files_created} 個檔案。\n")
        if self.created_files:
            self.root.after(0, lambda: self.show_files_button.config(state=tk.NORMAL))

    # --- 已更新 ---
    def create_source_code_bundle(self):
        output_filename = "all_source_code_bundle.txt"
        files_added = 0
        
        code_extensions = (
            '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.md',
            '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift',
            '.kt', '.ts', '.sql', '.sh', 'Dockerfile'
        )
        
        try:
            if getattr(sys, 'frozen', False):
                script_dir = os.path.dirname(sys.executable)
                script_to_exclude = os.path.basename(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                script_to_exclude = os.path.basename(os.path.abspath(__file__))

            self.log_output(f"🔍 開始掃描專案目錄： {script_dir}\n")
            self.log_output(f"📝 將會把結果儲存至： {output_filename}\n")
            self.log_output(f"🚫 將會排除目前執行的腳本： {script_to_exclude}\n\n") # 新增提示

            with open(output_filename, 'w', encoding='utf-8') as bundle_file:
                for root, _, files in os.walk(script_dir):
                    for filename in files:
                        # --- 主要修改處 ---
                        # 如果檔名是彙整檔本身，或是主程式腳本，就跳過
                        if filename == output_filename or filename == script_to_exclude:
                            continue

                        if filename.endswith(code_extensions):
                            file_path = os.path.join(root, filename)
                            relative_path = os.path.relpath(file_path, script_dir)
                            
                            self.log_output(f"  + 正在加入檔案: {relative_path}\n")
                            
                            bundle_file.write(f"\n{'='*20} FILE: {relative_path} {'='*20}\n\n")
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as source_file:
                                    content = source_file.read()
                                    bundle_file.write(content)
                                files_added += 1
                            except Exception as e:
                                self.log_output(f"    └─ ❌ 讀取檔案失敗: {e}\n")
                                bundle_file.write(f"*** 無法讀取此檔案內容: {e} ***\n")

            self.log_output(f"\n--- ✨ 全部完成！ ---\n")
            self.log_output(f"✅ 成功彙整 {files_added} 個檔案至 {output_filename}\n")
            
        except Exception as e:
            self.log_output(f"\n❌ 建立程式碼彙整檔時發生未預期的錯誤: {e}\n")
        finally:
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.show_all_button.config(state=tk.NORMAL, text="Show All Code"))

    def pre_parse_user_input(self, user_content):
        code_block_pattern = re.compile(r"""```(?:python|Python|py|)(.*?)```""", re.DOTALL)
        match = code_block_pattern.search(user_content)
        
        if match:
            file_content = match.group(1).strip()
            instructions = user_content.replace(match.group(0), "").strip()
            return instructions, file_content
        else:
            lines = user_content.strip().split('\n')
            non_code_lines = []
            code_lines = []
            in_code = False
            for line in lines:
                if line.startswith((' ', '\t', 'import ', 'def ', 'class ')) and not in_code:
                    in_code = True
                if in_code:
                    code_lines.append(line)
                else:
                    non_code_lines.append(line)
            
            if code_lines:
                return '\n'.join(non_code_lines), '\n'.join(code_lines)

        return user_content, None

    def generate_and_execute_plan(self):
        files_changed, commands_run, errors = 0, 0, 0
        try:
            user_content = self.input_text.get('1.0', tk.END)

            if not user_content.strip():
                self.log_output("輸入是空的。\n")
                return

            if self.is_path_map(user_content):
                self.create_structure_from_map(user_content)
                return

            ollama_url = self.ollama_url_entry.get()
            ollama_model = self.ollama_model_entry.get()
            
            self.log_output("正在預先解析輸入以分離指令和程式碼...\n")
            instructions, file_content = self.pre_parse_user_input(user_content)

            if not file_content:
                self.log_output("❌ 錯誤：無法在輸入中識別主要的程式碼區塊。\n")
                errors += 1
                return

            self.log_output("正在請求 Ollama 從指令中提取檔名和命令...\n")
            ai_plan_str = self.get_actions_from_ollama(ollama_url, ollama_model, instructions)
            
            if not ai_plan_str:
                errors += 1
                return

            actions = self.parse_raw_plan(ai_plan_str)

            file_action_added = False
            for action in actions:
                if action.get('type') == 'file':
                    action['content'] = file_content 
                    file_action_added = True
                    break
            
            if not file_action_added:
                self.log_output("⚠️ 警告：AI 未指定檔名，正在嘗試猜測...\n")
                guessed_filename_match = re.search(r'[\w.-]+\.py', instructions)
                if guessed_filename_match:
                    filename = guessed_filename_match.group(0)
                    actions.append({"type": "file", "path": filename, "content": file_content})
                    self.log_output(f"猜測的檔名是: {filename}\n")
                else:
                    self.log_output("❌ 錯誤：無法為程式碼區塊決定檔名。\n")
                    errors += 1

            if not actions:
                self.log_output("找不到任何有效的操作可執行。\n")
                errors += 1
                return

            self.log_output("--- 開始執行 ---\n")
            for action in actions:
                action_type = action.get('type')
                try:
                    if action_type == 'file' and action.get('path'):
                        self.execute_file_action(action.get('path'), action.get('content'))
                        files_changed += 1
                    elif action_type == 'shell':
                        success = self.execute_shell_action(action.get('command'))
                        commands_run += 1
                        if not success: errors += 1
                except Exception as e:
                    self.log_output(f"❌ 執行操作時發生錯誤: {e}\n")
                    errors += 1
            
            summary = f"\n--- ✨ 全部完成！ ---\n已建立/修改的檔案: {files_changed}\n已執行的命令: {commands_run}\n錯誤: {errors}\n"
            self.log_output(summary)
            
        except Exception as e:
            self.log_output(f"❌ 發生未預期的錯誤: {e}\n")
        finally:
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL, text="Generate and Execute Plan"))
            self.root.after(0, lambda: self.show_all_button.config(state=tk.NORMAL, text="Show All Code"))
            if self.created_files:
                self.root.after(0, lambda: self.show_files_button.config(state=tk.NORMAL))

    def get_actions_from_ollama(self, url, model, instructions):
        prompt = f'''You are an intelligent assistant that extracts a filename and setup commands from user instructions. The user's code has already been extracted. Focus ONLY on the instructions.

1.  **Filename**: Find the intended filename for the code (e.g., `my_script.py`). Format it like this:
    >>_PATH_START_<<
    {{filename}}
    >>_PATH_END_<<
    >>_CONTENT_START_<<
    {{leave_this_empty}}
    >>_CONTENT_END_<<

2.  **Shell Commands**: Find any setup commands, like `pip install`. Format each command individually:
    >>_SHELL_START_<<
    {{command_1}}
    >>_SHELL_END_<<

Analyze the following instructions and provide the plan. Your output must contain ONLY these special formatted blocks.

Instructions:
{instructions}'''

        data = {"model": model, "prompt": prompt, "stream": False}
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                response_text = response.read().decode('utf-8')
                
                if self.show_details_var.get():
                    self.log_output(f"--- DEBUG: Raw Ollama Response ---\n{response_text}\n--- END DEBUG ---\n\n")

                last_json_object = None
                for line in response_text.strip().split('\n'):
                    try: 
                        last_json_object = json.loads(line)
                    except json.JSONDecodeError: 
                        continue
                
                if not last_json_object:
                    try: 
                        last_json_object = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        self.log_output(f"❌ 錯誤：無法從 Ollama 解析 JSON: {e}\n")
                        return None

                plan_str = last_json_object.get('response', '').strip()
                
                if not plan_str:
                    self.log_output("❌ 錯誤：AI 回傳了空的計畫。\n")
                    return None
                return plan_str
        except Exception as e:
            self.log_output(f"❌ 與 Ollama 通訊時發生錯誤: {e}\n")
            return None

    def parse_raw_plan(self, raw_plan):
        actions = []
        file_pattern = re.compile(r">>_PATH_START_<<(.*?)>>_PATH_END_<<(.*?)>>_CONTENT_START_<<(.*?)>>_CONTENT_END_<<", re.DOTALL)
        shell_pattern = re.compile(r">>_SHELL_START_<<(.*?)>>_SHELL_END_<<", re.DOTALL)

        for match in file_pattern.finditer(raw_plan):
            path = match.group(1).strip()
            content = match.group(3).strip() 
            if path:
                actions.append({"type": "file", "path": path, "content": content})

        for match in shell_pattern.finditer(raw_plan):
            command_block = match.group(1).strip()
            for command in command_block.split('\n'):
                command = command.strip()
                if command and command.lower() not in ['bash', 'python', 'shell', 'cmd', 'code']:
                    actions.append({"type": "shell", "command": command})
        
        return actions

    def execute_file_action(self, path, content):
        if not path or content is None:
            self.log_output(f"❌ 錯誤：檔案操作缺少路徑或內容。路徑: {path}\n")
            return
        self.log_output(f"✅ 正在建立/修改檔案: {path}\n")
        dir_name = os.path.dirname(path)
        if dir_name: 
            os.makedirs(dir_name, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f: 
            f.write(content)
        self.created_files.append({'path': path, 'content': content})

    def execute_shell_action(self, command):
        if not command: 
            raise ValueError("Shell action requires 'command'.")
        start_message = f"⚙️ 好的，正在為您執行命令： {command}\n"
        if command.strip().startswith("pip install") or command.strip().startswith("npm install"):
            start_message = f"⚙️ 好的，正在為您安裝必要的東西： {command}\n"
        self.log_output(start_message)
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                self.log_output(f"✔️ 太棒了！命令順利完成了！\n")
                if self.show_details_var.get() and result.stdout:
                    self.log_output(f"以下是執行日誌：\n---\n{result.stdout}\n---\n")
                return True
            else:
                self.log_output(f"❌ 哎呀！命令執行失敗了。\n")
                if result.stderr: 
                    self.log_output(f"看起來是發生了這個錯誤：\n---\n{result.stderr}\n---\n")
                if result.stdout: 
                    self.log_output(f"這裡還有一些額外的輸出訊息：\n---\n{result.stdout}\n---\n")
                return False
        except Exception as e:
            self.log_output(f"❌ 在嘗試執行命令時發生了預期外的錯誤： {e}\n")
            return False

    def show_created_files(self):
        if not self.created_files:
            messagebox.showinfo("沒有檔案", "在上次執行中沒有建立任何檔案。")
            return

        top = tk.Toplevel(self.root)
        top.title("建立的檔案")
        top.configure(bg="#2E2E2E")
        self.center_window_toplevel(top, 800, 600)

        text_area = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=self.font_main, bg="#1E1E1E", fg="#D4D4D4", relief=tk.FLAT)
        text_area.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        for file_info in self.created_files:
            path = file_info['path']
            content = file_info['content']
            
            header = f"--- 檔案: {path} ---\n" 
            
            text_area.insert(tk.END, header)
            text_area.insert(tk.END, content + "\n\n")

        text_area.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = CodeAgentApp(root)
    root.mainloop()