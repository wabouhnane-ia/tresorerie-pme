import ast, traceback
p='backend/app/reporting/pdf_report.py'
try:
    s=open(p,'r',encoding='utf-8').read()
    ast.parse(s, p)
    print('OK')
except Exception as e:
    traceback.print_exc()
    print('ERR', e)
