import './style.css';
import {formats,routes,getFormat,targetsFor,detectFormats,inputFormats,categories} from './registry.js';
import {convertFile,cancelEngines} from './engines.js';
import {zipSync} from 'fflate';
const $=id=>document.getElementById(id);
let files=[],busy=false,epoch=0,limit=48,resultURLs=[],successful=[];
const size=n=>n<1024*1024?`${(n/1024).toFixed(1)} KiB`:`${(n/1024/1024).toFixed(1)} MiB`;
const sorted=[...inputFormats].sort((a,b)=>a.category.localeCompare(b.category)||a.name.localeCompare(b.name));
function option(value,text){const o=document.createElement('option');o.value=value;o.textContent=text;return o;}
for(const category of categories){const fs=sorted.filter(f=>f.category===category);if(!fs.length)continue;const g=document.createElement('optgroup');g.label=category;fs.forEach(f=>g.append(option(f.id,`${f.name} (.${f.ext})`)));$('source-format').append(g);$('category-filter').append(option(category,category));}
function status(message,state=''){const box=$('status');box.className='status '+state;box.querySelector('.status-icon').textContent=state==='error'?'!':state==='busy'?'◌':'✓';box.lastElementChild.textContent=message;}
function updateOutput(preferred){
 const source=getFormat($('source-format').value),options=targetsFor(source.id),select=$('target-format');select.replaceChildren();
 for(const route of options){const f=getFormat(route.to);select.append(option(f.id,`${f.name} (.${f.ext})`));}
 const defaults={document:'pdf:pdf',image:'image:png',table:'table:csv',array:'array:csv',spectrum:'spectrum:csv',atom:'atom:xyz',mesh:'mesh:stl',sequence:'sequence:fasta',config:'config:json',geo:'geo:geojson',media:source.category==='Video'?'media:mp3':source.category==='Subtitles'?'media:vtt':'media:wav',pdf:'pdf:png',font:'font:woff2',archive:'archive:zip',compression:'compression:bin'};
 const value=preferred||defaults[source.engine];if(options.some(r=>r.to===value))select.value=value;
 $('target-count').textContent=`${options.length} outputs`;updateDescription();updateButton();
}
function updateDescription(){const to=getFormat($('target-format').value),route=targetsFor($('source-format').value).find(r=>r.to===to?.id);$('output-extension').textContent=to?.ext.toUpperCase()||'—';$('output-title').textContent=to?.name||'No compatible outputs';$('route-note').textContent=route?.note||'';}
function routeFor(file){const target=$('target-format').value,selected=$('source-format').value,source=getFormat(selected);const matches=detectFormats(file.name);const same=matches.find(f=>f.id===selected)||matches.find(f=>f.engine===source.engine&&routes.some(r=>r.from===f.id&&r.to===target));if(same)return routes.find(r=>r.from===same.id&&r.to===target);return files.length===1?routes.find(r=>r.from===selected&&r.to===target):null;}
function updateButton(){const button=$('convert');button.disabled=busy||files.length===0||!files.some(routeFor);button.textContent=busy?'Converting locally…':files.length?`Convert ${files.length===1?'file':files.length+' files'}`:'Choose a file to start';$('cancel').hidden=!busy;for(const id of ['source-format','target-format','file-input','companions','clear-files'])$(id).disabled=busy;$('dropzone').setAttribute('aria-disabled',String(busy));}
function renderFiles(){
 const list=$('file-list');list.replaceChildren();$('clear-files').hidden=!files.length;$('input-count').textContent=files.length?`${files.length} selected`:'Your file';
 for(const file of files){const row=document.createElement('div');row.className='file-row';const n=document.createElement('span');n.textContent=file.name;const s=document.createElement('span');s.textContent=size(file.size);row.append(n,s);list.append(row);}
 updateButton();
}
function addFiles(incoming){if(busy)return;const list=Array.from(incoming);const tooLarge=list.filter(f=>f.size>128*1024*1024);files=list.filter(f=>f.size<=128*1024*1024);successful=[];
 for(const u of resultURLs)URL.revokeObjectURL(u);resultURLs=[];$('results').replaceChildren();
 const current=getFormat($('source-format').value);const detected=files[0]?detectFormats(files[0].name):[];const match=detected.find(f=>f.engine===current.engine)||detected[0];
 if(match){$('source-format').value=match.id;updateOutput();status('Ready. Choose an output format and convert.');}
 else if(files.length)status('This extension is not recognized. Choose its actual input format manually, or create a ZIP below.','error');
 if(tooLarge.length)status(`${tooLarge.length} file(s) exceeded 128 MiB and were skipped.`,'error');
 renderFiles();if(files.length)addPackButton();
}
function addPackButton(){const existing=$('pack-files');if(existing)existing.remove();const b=document.createElement('button');b.id='pack-files';b.className='text-button';b.textContent='Or package selected files as ZIP';b.style.margin='8px 0';b.addEventListener('click',()=>{const data={};const used=new Set();Promise.all(files.map(async(f,i)=>{let name=f.name;if(used.has(name))name=`${i+1}-${name}`;used.add(name);data[name]=new Uint8Array(await f.arrayBuffer());})).then(()=>{showResult('files.zip',{bytes:zipSync(data),ext:'zip'});status('ZIP created locally.');}).catch(e=>status(e.message,'error'));});$('results').append(b);}
function showResult(name,result,error){const row=document.createElement('div');row.className='result-row'+(error?' error':'');const info=document.createElement('div'),title=document.createElement('strong'),detail=document.createElement('small');title.textContent=name;detail.textContent=error||`${size(result.bytes.length)}${result.warnings?' · '+result.warnings:''}`;info.append(title,detail);row.append(info);
 if(!error){const blob=new Blob([result.bytes],{type:result.ext==='pdf'?'application/pdf':'application/octet-stream'}),url=URL.createObjectURL(blob);resultURLs.push(url);const a=document.createElement('a');a.href=url;a.download=name;a.textContent='Download';row.append(a);successful.push({name,bytes:result.bytes});}
 $('results').append(row);
}
function addDownloadAll(){if(successful.length<2)return;const b=document.createElement('button');b.className='secondary';b.style.margin='12px 0 18px';b.textContent='Download all as ZIP';b.onclick=()=>{const entries={};successful.forEach((r,i)=>{entries[entries[r.name]?`${i+1}-${r.name}`:r.name]=r.bytes;});const url=URL.createObjectURL(new Blob([zipSync(entries)],{type:'application/zip'}));resultURLs.push(url);const a=document.createElement('a');a.href=url;a.download='converted-files.zip';a.click();};$('results').append(b);}
$('convert').onclick=async()=>{
 busy=true;const myEpoch=++epoch;updateButton();successful=[];for(const u of resultURLs)URL.revokeObjectURL(u);resultURLs=[];$('results').replaceChildren();let done=0,failed=0;
 const options={quality:Number($('quality').value)||92,dataset:$('dataset').value,delimiter:$('delimiter').value,skipRows:Number($('skip-rows').value)||0};
 try{for(let i=0;i<files.length;i++){
  if(epoch!==myEpoch)return;const file=files[i],route=routeFor(file);
  if(!route){showResult(file.name,null,'This file has no route to the selected output. Choose its input format first.');failed++;continue;}
  try{const result=await convertFile(file,route,options,m=>{if(epoch===myEpoch)status(`${files.length>1?`File ${i+1}/${files.length}: `:''}${m}`,'busy');},Array.from($('companions').files));if(epoch!==myEpoch)return;
   const ext=getFormat(route.from).ext;const stem=file.name.toLowerCase().endsWith('.'+ext)?file.name.slice(0,-ext.length-1):file.name.replace(/\.[^.]*$/,'');
   showResult(stem+'.'+result.ext,result);done++;
  }catch(e){if(epoch!==myEpoch)return;showResult(file.name,null,e.message);failed++;}
 }if(epoch===myEpoch){status(`${done} conversion${done===1?'':'s'} complete${failed?`; ${failed} could not be converted. See the details below.`:'. Your downloads are ready.'}`,failed?'error':'');addDownloadAll();}}
 finally{if(epoch===myEpoch){busy=false;updateButton();}}
};
$('cancel').onclick=()=>{epoch++;cancelEngines();busy=false;updateButton();status('Conversion canceled. You can choose another file or try again.');};
$('source-format').onchange=()=>{updateOutput();if(files.length)status('Input format changed. Check the output and conversion notes.');};$('target-format').onchange=()=>{updateDescription();updateButton();};
$('file-input').onchange=e=>{addFiles(e.target.files);e.target.value='';};$('clear-files').onclick=()=>{files=[];renderFiles();$('results').replaceChildren();status('Choose files to begin.');};
const zone=$('dropzone');zone.onclick=()=>{if(!busy)$('file-input').click();};zone.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();zone.click();}};
for(const event of ['dragenter','dragover'])zone.addEventListener(event,e=>{e.preventDefault();if(!busy)zone.classList.add('dragging');});for(const event of ['dragleave','drop'])zone.addEventListener(event,e=>{e.preventDefault();zone.classList.remove('dragging');});zone.addEventListener('drop',e=>addFiles(e.dataTransfer.files));
for(const b of document.querySelectorAll('[data-pair]'))b.onclick=()=>{if(busy)return;const [from,to]=b.dataset.pair.split('|');$('source-format').value=from;updateOutput(to);$('source-format').focus();};
const catalogSorted=[...formats].sort((a,b)=>a.category.localeCompare(b.category)||a.name.localeCompare(b.name));
function renderCatalog(){const term=$('format-search').value.trim().toLowerCase(),cat=$('category-filter').value;const matching=catalogSorted.filter(f=>(!cat||f.category===cat)&&`${f.name} ${f.ext} ${f.category} ${f.category==='Spectroscopy & diffraction'?'XRD FTIR Raman spectrum':''} ${f.category==='Scientific arrays'?'MATLAB NumPy HDF scientific':''}`.toLowerCase().includes(term));
 $('search-count').textContent=`${matching.length} formats${cat?' in '+cat:''}`;const grid=$('format-grid');grid.replaceChildren();for(const f of matching.slice(0,limit)){const count=targetsFor(f.id).length;const b=document.createElement('button');b.className='format-card'+(!count?' output-only':'');b.disabled=!count;const ext=document.createElement('span');ext.className='ext';ext.textContent='.'+f.ext;const info=document.createElement('div'),name=document.createElement('strong'),meta=document.createElement('small');name.textContent=f.name;meta.textContent=`${f.category} · ${count?count+' outputs':'Output only'}`;info.append(name,meta);b.append(ext,info);b.onclick=()=>{if(busy)return;$('source-format').value=f.id;updateOutput();document.querySelector('.converter').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});};grid.append(b);}
 if(!matching.length){const p=document.createElement('p');p.className='empty-grid';p.textContent='No formats match. Try an extension or choose another category.';grid.append(p);}$('show-more').hidden=matching.length<=limit;for(const b of $('category-chips').children)b.classList.toggle('active',b.dataset.category===cat);
}
for(const cat of ['Documents','Images','Spectroscopy & diffraction','Scientific arrays','Crystals & atomic structures','3D meshes & simulation','Audio','Video']){const b=document.createElement('button');b.textContent=cat;b.dataset.category=cat;b.onclick=()=>{$('category-filter').value=$('category-filter').value===cat?'':cat;limit=48;renderCatalog();};$('category-chips').append(b);}
$('format-search').oninput=$('category-filter').onchange=()=>{limit=48;renderCatalog();};$('show-more').onclick=()=>{limit+=96;renderCatalog();};
$('catalog-count').textContent=`${inputFormats.length} input formats across ${categories.length} categories, with ${routes.length.toLocaleString()} defined conversion routes.`;
$('download-catalog').onclick=e=>{e.preventDefault();const lines=['# Everything Converter web format catalog','','Input formats: '+inputFormats.length,'Defined routes: '+routes.length,'','Files are processed locally. A route does not guarantee every file variant is supported.',''];for(const category of categories){lines.push('## '+category,'');for(const f of formats.filter(x=>x.category===category)){const rs=targetsFor(f.id);lines.push(`- ${f.name} (.${f.ext}): ${rs.length?rs.map(r=>'.'+getFormat(r.to).ext).join(', '):'output only'}`);}lines.push('');}const url=URL.createObjectURL(new Blob([lines.join('\n')],{type:'text/markdown'}));resultURLs.push(url);const a=document.createElement('a');a.href=url;a.download='Everything_Converter_Formats.md';a.click();};
$('source-format').value='document:docx';updateOutput();renderCatalog();
