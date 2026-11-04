from pathlib import Path
import ast,sys
p=Path(sys.argv[1]); tree=ast.parse(p.read_text()); tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='main')];ns={'__name__':'finite_resource_probe'};exec(compile(tree,str(p),'exec'),ns);ns['build'](1,0.2,'title1.png','center','in')
