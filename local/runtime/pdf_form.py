"""Fill existing AcroForm text fields with embedded Unicode appearances.

Input PDF and field JSON are user resources. No task-specific field names or
values are built in. Output remains interactive; original pages are cloned,
not rasterized or flattened. Signed/encrypted/ambiguous forms are rejected.
"""
from __future__ import annotations
import argparse,hashlib,io,json,math,re
from pathlib import Path
import pymupdf
from pypdf import PdfReader,PdfWriter
from pypdf.generic import (NameObject,TextStringObject,BooleanObject,DictionaryObject,
                           DecodedStreamObject,ArrayObject,FloatObject)

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def deref(v):return v.get_object() if hasattr(v,'get_object') else v
def identity(obj):
 ref=getattr(obj,'indirect_reference',None)
 return (ref.idnum,ref.generation) if ref is not None else id(obj)
def inherited(obj,key,default=None):
 seen=set()
 while obj is not None:
  obj=deref(obj)
  if identity(obj) in seen:raise ValueError('Cyclic field parent chain')
  seen.add(identity(obj))
  if key in obj:return obj[key]
  obj=obj.get('/Parent')
 return default
def widget_name_owner(widget):
 parts=[];owner=None;obj=widget;seen=set()
 while obj is not None:
  obj=deref(obj)
  if identity(obj) in seen:raise ValueError('Cyclic field parent chain')
  seen.add(identity(obj))
  if '/T' in obj:
   parts.append(str(obj['/T']))
   if owner is None:owner=obj
  obj=obj.get('/Parent')
 return '.'.join(reversed(parts)),owner
def canonical_fields(acro):
 fields={};seen=set()
 def visit(ref,prefix='',ft=None):
  obj=deref(ref);key=identity(obj)
  if key in seen:raise ValueError('Repeated/cyclic field tree object')
  seen.add(key);name=str(obj.get('/T',''));full='.'.join(x for x in [prefix,name] if x);ft=obj.get('/FT',ft);kids=[deref(x) for x in obj.get('/Kids',[])]
  if ft=='/Sig' and obj.get('/V'):raise ValueError('Signed PDF cannot be edited by this helper')
  if name and not any('/T' in kid for kid in kids):
   if full in fields:raise ValueError('Ambiguous duplicate canonical field name: '+full)
   fields[full]=obj
  for kid in kids:visit(kid,full,ft)
 for ref in acro.get('/Fields',[]):visit(ref)
 return fields
def color(value,default):
 if value is None:return default
 v=[float(x) for x in value]
 if len(v) not in [1,3,4] or any(not math.isfinite(x) or not 0<=x<=1 for x in v):raise ValueError('Invalid field color')
 return tuple(v)
def fill_pdf(source,values,output,font_file=None):
 source=Path(source).resolve();output=Path(output).resolve()
 if output==source or output.exists():raise ValueError('Preserve input/existing output; choose a fresh output path')
 if not source.is_file() or source.is_symlink():raise ValueError('Input must be an existing regular PDF')
 if not isinstance(values,dict) or not values or any(not isinstance(k,str) or not k for k in values):raise ValueError('Fields JSON must be a nonempty object keyed by exact field names')
 clean={}
 for k,v in values.items():
  if isinstance(v,str):clean[k]=v
  elif type(v) in [int,float] and math.isfinite(v):clean[k]=str(v)
  else:raise ValueError('Field values must be strings or finite numbers: '+k)
 original_sha=digest(source);reader=PdfReader(source)
 if reader.is_encrypted:raise ValueError('Encrypted PDF requires an explicit decryption workflow')
 writer=PdfWriter();writer.clone_document_from_reader(reader)
 acro=deref(writer.root_object.get('/AcroForm'))
 if not isinstance(acro,dict):raise ValueError('PDF has no canonical AcroForm tree')
 if '/XFA' in acro:raise ValueError('XFA forms require a separate explicit workflow')
 fields=canonical_fields(acro);missing=set(clean)-set(fields)
 if missing:raise ValueError('Unknown canonical text field names: '+', '.join(sorted(missing)))
 for name in clean:
  obj=fields[name]
  if inherited(obj,'/FT')!='/Tx':raise ValueError('Only existing text fields are supported: '+name)
  flags=int(inherited(obj,'/Ff',0))
  if flags&1:raise ValueError('Read-only field requires a separate explicit workflow: '+name)
  if flags&(1<<13):raise ValueError('Password fields are not rendered by this helper')
  if '\n' in clean[name] and not flags&(1<<12):raise ValueError('Newline supplied for a single-line field: '+name)
  maximum=inherited(obj,'/MaxLen')
  if maximum is not None and len(clean[name])>int(maximum):raise ValueError('Field MaxLen exceeded: '+name)
 slots=[]
 for page_index,page in enumerate(writer.pages):
  for ref in page.get('/Annots',[]):
   widget=deref(ref)
   if widget.get('/Subtype')!='/Widget':continue
   name,owner=widget_name_owner(widget)
   if name not in clean:continue
   if owner is None or identity(owner)!=identity(fields[name]):raise ValueError('Widget/canonical field ambiguity: '+name)
   rect=[float(x) for x in widget['/Rect']];w=abs(rect[2]-rect[0]);h=abs(rect[3]-rect[1])
   if min(w,h)<=0:raise ValueError('Zero-size field: '+name)
   rotation=int(deref(widget.get('/MK',{})).get('/R',0))%360
   if rotation:raise ValueError('Rotated widgets require a separate rendering workflow: '+name)
   slots.append((widget,name,page_index,w,h))
 if set(clean)!=set(x[1] for x in slots):raise ValueError('Requested field has no page widget')
 font=pymupdf.Font(fontfile=str(font_file)) if font_file else pymupdf.Font('cjk')
 for name,value in clean.items():
  if any(not ch.isspace() and not font.has_glyph(ord(ch)) for ch in value):raise ValueError('Selected font has no glyph for a field character: '+name)
 scratch=pymupdf.open();details=[]
 for widget,name,page_index,w,h in slots:
  page=scratch.new_page(width=w,height=h);mk=deref(widget.get('/MK',{}));bs=deref(widget.get('/BS',{}));border=float(bs.get('/W',widget.get('/Border',[0,0,1])[2]));background=color(mk.get('/BG'),None);stroke=color(mk.get('/BC'),None)
  if background is not None or stroke is not None:page.draw_rect(page.rect,color=stroke,fill=background,width=border if stroke is not None else 0)
  page.insert_font(fontname='EvalFormFont',fontbuffer=font.buffer)
  da=str(inherited(widget,'/DA','/Helv 12 Tf 0 g'));match=re.search(r'([0-9.]+)\s+Tf',da);size=float(match.group(1)) if match else 12
  size=size if size>0 else min(12,h-4);padding=max(2,border+1);box=pymupdf.Rect(padding,padding,w-padding,h-padding);align=int(inherited(widget,'/Q',0))
  # Probe in a disposable page until all lines fit; never silently clip text.
  while size>=4:
   probe=pymupdf.open();pp=probe.new_page(width=w,height=h);pp.insert_font(fontname='EvalFormFont',fontbuffer=font.buffer);fits=pp.insert_textbox(box,clean[name],fontname='EvalFormFont',fontsize=size,align=align);probe.close()
   if fits>=0:break
   size-=0.5
  if size<4:raise ValueError('Text does not fit field at readable size: '+name)
  page.insert_textbox(box,clean[name],fontname='EvalFormFont',fontsize=size,align=align,color=(0,0,0));details.append({'name':name,'page_index':page_index,'font_size':size,'rect':list(widget['/Rect'])})
 # Shared full font covers later edits; unlike a current-value subset it does
 # not make new Chinese characters disappear when a viewer regenerates AP.
 appearance_reader=PdfReader(io.BytesIO(scratch.tobytes(garbage=4,deflate=True)))
 font_resource=None
 for index,(widget,name,_,w,h) in enumerate(slots):
  ap_page=appearance_reader.pages[index];resources=deref(ap_page['/Resources']).clone(writer);stream=DecodedStreamObject();stream.set_data(ap_page.get_contents().get_data());stream.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Form'),NameObject('/BBox'):ArrayObject([FloatObject(0),FloatObject(0),FloatObject(w),FloatObject(h)]),NameObject('/Resources'):resources})
  ap=DictionaryObject({NameObject('/N'):writer._add_object(stream)});widget[NameObject('/AP')]=ap;fields[name][NameObject('/V')]=TextStringObject(clean[name]);widget[NameObject('/V')]=TextStringObject(clean[name]);widget[NameObject('/DA')]=TextStringObject('/EvalFormFont '+str(details[index]['font_size'])+' Tf 0 g');fields[name][NameObject('/DA')]=widget['/DA'];font_resource=deref(resources['/Font'])['/EvalFormFont']
 dr=deref(acro.get('/DR',DictionaryObject()));fonts=deref(dr.get('/Font',DictionaryObject()));fonts[NameObject('/EvalFormFont')]=font_resource;dr[NameObject('/Font')]=fonts;acro[NameObject('/DR')]=dr;acro[NameObject('/NeedAppearances')]=BooleanObject(False)
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:writer.write(f)
 scratch.close();reopened=PdfReader(output);actual=reopened.get_fields() or {}
 if len(reopened.pages)!=len(reader.pages) or any(name not in actual or str(actual[name].get('/V',''))!=value for name,value in clean.items()):raise RuntimeError('Saved form field/page round-trip failed')
 if digest(source)!=original_sha:raise RuntimeError('Input PDF changed unexpectedly')
 return {'source_sha256':original_sha,'output_sha256':digest(output),'output_bytes':output.stat().st_size,'updated_fields':details,'field_names':sorted(clean),'page_count':len(reopened.pages),'flattened':False,'font_embedded_full':True,'original_source_unchanged':True,'scope':'field values and generated appearances; caller must render/inspect final output'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input_pdf',type=Path);p.add_argument('fields_json',type=Path);p.add_argument('output_pdf',type=Path);p.add_argument('--font-file',type=Path);p.add_argument('--receipt',type=Path);a=p.parse_args();result=fill_pdf(a.input_pdf,json.loads(a.fields_json.read_text(encoding='utf-8-sig')),a.output_pdf,a.font_file)
 if a.receipt:
  if a.receipt.exists():raise ValueError('Receipt already exists')
  a.receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
