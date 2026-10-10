# Methodology: Handling Large Texts in Multi-Step Editing
## Problem: Large Text Editing in Multi-Step Workflows
The editor tool has a ~6000 character limit for new_text. When creating large documents (10,000+ lines), content must be split into smaller chunks and appended incrementally using insert_line.
## Solution: Incremental Append Strategy
### Step 1: Create Master Skeleton First
Create the main markdown file with table of contents and section headers only. This establishes the structure without hitting size limits.
### Step 2: Write Section Content to Separate Temp Files
Write each major section (2000-5000 lines) to its own temp markdown file. This keeps individual edits under the 6000-char limit.
Use descriptive filenames: section_01_executive_summary.md, section_02_foundations.md, etc.
### Step 3: Append Sections Incrementally Using insert_line
Read the master file to find the current line count, then use insert_line at EOF (line_count + 1) to append each section.
Append sections one at a time, verifying line count after each. If a section is >6000 chars, split it further and append in sub-chunks.
### Step 4: Use PowerShell for Bulk Appends When Possible
For very large sections, write content to a temp file using PowerShell Add-Content, then append the entire file to master using Get-Content | Add-Content.
### Step 5: Verify and Track Progress
After each append: run Get-Content file | Measure-Object -Line to verify line count increased as expected.
Keep a running log of line counts per section in a tracking document.
If an append fails or truncates: re-read the master file, find the last valid line, and resume from there using insert_line.
### Key PowerShell Commands Reference
`powershell
# Check line count
Get-Content file.md | Measure-Object -Line
# Append single line
Add-Content -Path file.md -Value  text -Encoding utf8
# Append entire file to master
Get-Content temp.md | Add-Content -Path master.md -Encoding utf8
# Editor tool insert at EOF
insert_line: line_count + 1 (at EOF)
`
## Lessons Learned
1. Always verify line count after each append - silent truncation is the biggest risk
2. Split large sections into temp files first - never try to insert >6000 chars in one go
3. Use PowerShell for bulk operations - faster and more reliable than repeated editor calls
4. Keep all temp files and intermediate versions - enables recovery if something goes wrong
5. Track progress in a separate log - line counts per section, timestamps, status
---
