import json
import os

json_file = r"c:\Users\abhin\Desktop\AEGIS-OT\aegis-ot\frontend\run_results.json"
output_md = r"C:\Users\abhin\.gemini\antigravity-ide\brain\ef99a26d-dda0-4003-ab8b-9835d0142b02\command_results.md"

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

md_content = "# AEGIS-OT Command Runbook Results\n\n"
md_content += "The following are the results of the executed commands from the runbook:\n\n"

for cmd, output in data.items():
    md_content += f"## {cmd}\n"
    # Limit output if it's too long
    if len(output) > 2000:
        md_content += "```text\n" + output[:1000] + "\n...[truncated]...\n" + output[-1000:] + "\n```\n\n"
    else:
        md_content += "```text\n" + output + "\n```\n\n"

with open(output_md, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Artifact created at: {output_md}")
