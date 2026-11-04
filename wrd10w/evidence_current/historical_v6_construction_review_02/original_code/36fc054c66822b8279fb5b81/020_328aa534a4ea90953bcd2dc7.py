s=open('work_runpy.txt',encoding='utf-8').read()
# print the section after checks 1-3: report assembly and stdout part
i = s.find('# 3) 样式与布局保持')
j = s.find('def ') 
print(s[15000:])