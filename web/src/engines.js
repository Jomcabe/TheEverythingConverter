import { getFormat } from './registry.js';
import { zipSync, gzipSync, strToU8 } from 'fflate';
let scienceWorker,wasmWorker,ffmpeg;
const workers=new Set();
const pending=new Set();
export function cancelEngines(){for(const stop of [...pending])stop();for(const w of workers)w.terminate();workers.clear();scienceWorker=wasmWorker=null;if(ffmpeg){try{ffmpeg.terminate();}catch{}ffmpeg=null;}}
function request(worker,data,onStatus){return new Promise((resolve,reject)=>{
 const onMessage=({data:d})=>{if(d.type==='status')onStatus(d.message);else{cleanup();d.type==='result'?resolve(d):reject(new Error(d.message));}};
 const onError=e=>{cleanup();reject(new Error(e.message||'The conversion engine stopped. Try a smaller file.'));};
 const stop=()=>{cleanup();reject(new Error('Conversion canceled.'));};
 const cleanup=()=>{pending.delete(stop);worker.removeEventListener('message',onMessage);worker.removeEventListener('error',onError);};
 pending.add(stop);worker.addEventListener('message',onMessage);worker.addEventListener('error',onError);worker.postMessage(data,[data.bytes.buffer,...(data.companions||[]).map(f=>f.bytes.buffer)]);
});}
function getWorker(type){
 if(type==='science'){if(!scienceWorker){scienceWorker=new Worker(import.meta.env.BASE_URL+'python-worker.js');workers.add(scienceWorker);}return scienceWorker;}
 if(!wasmWorker){wasmWorker=new Worker(new URL('./wasm-worker.js',import.meta.url),{type:'module'});workers.add(wasmWorker);}return wasmWorker;
}
function image(bytes,source,target,options,onStatus){return request(getWorker('wasm'),{engine:'image',bytes,readCoder:source.coder,coder:target.coder||'PNG',options},onStatus);}
async function pdfFromImage(bytes,ext){
 const {PDFDocument}=await import('pdf-lib');const pdf=await PDFDocument.create();const img=ext==='jpg'||ext==='jpeg'?await pdf.embedJpg(bytes):await pdf.embedPng(bytes);
 const scale=Math.min(1,14400/Math.max(img.width,img.height));const page=pdf.addPage([img.width*scale,img.height*scale]);page.drawImage(img,{x:0,y:0,width:img.width*scale,height:img.height*scale});return pdf.save();
}
export async function htmlToPDF(bytes,media=[]){
 const [{default:DOMPurify},{default:htmlToPdfmake},pdfMod,fontMod]=await Promise.all([import('dompurify'),import('html-to-pdfmake'),import('pdfmake/build/pdfmake'),import('pdfmake/build/vfs_fonts')]);
 const pdfMake=pdfMod.default;pdfMake.addVirtualFileSystem(fontMod.default);
 const html=new TextDecoder().decode(bytes);
 const clean=DOMPurify.sanitize(html,{FORBID_TAGS:['script','style','iframe','object','embed','link','meta','form'],FORBID_ATTR:['srcset']});
 const doc=new DOMParser().parseFromString(clean,'text/html');
 const mediaMap=new Map(media.map(f=>[f.name,f.bytes]));
 for(const img of doc.images){
  const src=img.getAttribute('src')||'';
  const data=mediaMap.get(src)||mediaMap.get(src.replace(/^\.\//,''));
  if(data){const type=/\.jpe?g$/i.test(src)?'image/jpeg':/\.svg$/i.test(src)?'image/svg+xml':'image/png';img.src=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(new Blob([data],{type}));});}
  if(!/^data:image\/(png|jpeg);base64,/i.test(img.src)){img.replaceWith(doc.createTextNode(img.alt||'[Image omitted]'));continue;}
  img.setAttribute('width','450');img.removeAttribute('height');
 }
 let content=htmlToPdfmake(doc.body.innerHTML,{window,defaultStyles:{p:{margin:[0,0,0,7]},h1:{fontSize:22,margin:[0,10,0,10]},table:{margin:[0,5,0,8]}}});
 return new Promise((resolve,reject)=>{try{pdfMake.createPdf({pageSize:'A4',pageMargins:[42,42,42,42],defaultStyle:{font:'Roboto',fontSize:10},content}).getBuffer(b=>resolve(new Uint8Array(b)));}catch(e){reject(e);}});
}
async function documentConvert(bytes,from,to,options,onStatus,companions){
 const result=await request(getWorker('wasm'),{engine:'document',bytes,ext:from.ext,target:to.ext,from:from.pandoc,to:to.ext==='pdf'?'html':to.ext==='txt'?'plain':to.pandoc,options,companions},onStatus);
 if(to.ext==='pdf'){onStatus('Laying out the PDF locally…');return {bytes:await htmlToPDF(result.bytes,result.media),ext:'pdf',warnings:result.stderr};}
 if(result.media.length&&!['docx','odt','epub','pptx'].includes(to.ext)){
  const entries={['document.'+to.ext]:result.bytes};for(const f of result.media)entries[f.name]=f.bytes;
  return {bytes:zipSync(entries),ext:'zip',warnings:'Document and companion images are included in this ZIP.'};
 }
 return {bytes:result.bytes,ext:to.ext,warnings:result.stderr};
}
async function pdfConvert(bytes,to,options,onStatus){
 const pdfjs=await import('pdfjs-dist');pdfjs.GlobalWorkerOptions.workerSrc=import.meta.env.BASE_URL+'pdf.worker.min.mjs';
 const task=pdfjs.getDocument({data:bytes,isEvalSupported:false,useSystemFonts:true,cMapUrl:'https://cdn.jsdelivr.net/npm/pdfjs-dist@5.4.394/cmaps/',cMapPacked:true,standardFontDataUrl:'https://cdn.jsdelivr.net/npm/pdfjs-dist@5.4.394/standard_fonts/',wasmUrl:'https://cdn.jsdelivr.net/npm/pdfjs-dist@5.4.394/wasm/'});
 let pdf;
 try{
  pdf=await task.promise;const text=[],entries={};
  for(let n=1;n<=pdf.numPages;n++){
   onStatus(`Reading PDF page ${n} of ${pdf.numPages}…`);const page=await pdf.getPage(n);
   if(['png','jpg'].includes(to.ext)){
    const viewport=page.getViewport({scale:Math.min(2,8192/Math.max(page.view[2],page.view[3]))});
    const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
    await page.render({canvasContext:canvas.getContext('2d'),viewport,background:'#ffffff'}).promise;
    const blob=await new Promise(r=>canvas.toBlob(r,to.ext==='jpg'?'image/jpeg':'image/png',(options.quality||92)/100));
    entries[`page-${String(n).padStart(3,'0')}.${to.ext}`]=new Uint8Array(await blob.arrayBuffer());canvas.width=canvas.height=0;
   }else{const tc=await page.getTextContent();text.push(tc.items.map(i=>i.str+(i.hasEOL?'\n':' ')).join('').replace(/[ \t]+/g,' ').replace(/ *\n */g,'\n').trim());}
   page.cleanup();
  }
  if(['png','jpg'].includes(to.ext))return {bytes:zipSync(entries),ext:'zip'};
  const plain=text.join('\n\n');const escaped=plain.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  if(to.ext==='docx')return documentConvert(strToU8(plain),{ext:'txt',pandoc:'markdown'},{ext:'docx',pandoc:'docx'},options,onStatus,[]);
  return {bytes:strToU8(to.ext==='html'?`<!doctype html><meta charset="utf-8"><pre>${escaped}</pre>`:plain),ext:to.ext,warnings:plain.trim()?'':'This PDF has no selectable text. Use OCR on the scanned pages first.'};
 }finally{if(pdf)await pdf.destroy();else await task.destroy();}
}
async function mediaConvert(bytes,from,to,options,onStatus){
 if(!ffmpeg){onStatus('Loading the audio/video engine (about 32 MB on the first use)…');
  const {FFmpeg}=await import('@ffmpeg/ffmpeg');const f=new FFmpeg();
  const blobURL=async(url,type)=>{const r=await fetch(url);if(!r.ok)throw new Error('Media engine download failed.');return URL.createObjectURL(new Blob([await r.arrayBuffer()],{type}));};
  const base='https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/esm';const urls=[];
  try{urls.push(await blobURL(base+'/ffmpeg-core.js','text/javascript'),await blobURL(base+'/ffmpeg-core.wasm','application/wasm'));await f.load({coreURL:urls[0],wasmURL:urls[1]});ffmpeg=f;}catch(e){f.terminate();throw e;}finally{urls.forEach(u=>URL.revokeObjectURL(u));}
 }
 const f=ffmpeg,src='input.'+from.ext,dst='output.'+to.ext;const logs=[];
 const log=({message})=>{logs.push(message);if(logs.length>20)logs.shift();};
 const progress=({progress})=>{if(progress>=0&&progress<=1)onStatus(`Converting media locally… ${Math.round(progress*100)}%`);};
 f.on('log',log);f.on('progress',progress);
 try{
  await f.writeFile(src,bytes);let args=['-i',src];
  const audio={mp3:['-c:a','libmp3lame','-b:a','192k'],wav:['-c:a','pcm_s16le'],flac:['-c:a','flac'],ogg:['-c:a','libvorbis'],opus:['-c:a','libopus'],m4a:['-c:a','aac','-b:a','192k'],aac:['-c:a','aac'],aiff:['-c:a','pcm_s16be'],ac3:['-c:a','ac3'],au:['-c:a','pcm_s16be']};
  const video={mp4:['-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart'],mov:['-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac'],mkv:['-c:v','libx264','-c:a','aac'],webm:['-c:v','libvpx','-b:v','1M','-c:a','libopus'],avi:['-c:v','mpeg4','-c:a','libmp3lame'],ogv:['-c:v','libtheora','-c:a','libvorbis'],mpg:['-c:v','mpeg2video','-c:a','mp2'],flv:['-c:v','flv','-c:a','libmp3lame'],ts:['-c:v','libx264','-c:a','aac']};
  if(from.category==='Subtitles')args.push('-map','0:s:0');
  else if(audio[to.ext])args.push('-vn',...audio[to.ext]);
  else if(to.ext==='gif')args.push('-vf','fps=12,scale=min(720\\,iw):-1:flags=lanczos','-loop','0');
  else if(video[to.ext])args.push(...video[to.ext]);
  args.push('-threads','1','-y',dst);
  const result=await f.exec(args);if(result!==0)throw new Error(logs.slice(-6).join('\n')||'Unsupported codec or damaged media file.');
  return {bytes:await f.readFile(dst),ext:to.ext};
 }finally{for(const file of [src,dst]){try{await f.deleteFile(file);}catch{}}f.off('log',log);f.off('progress',progress);}
}
async function svgToPNG(bytes,ext){
 if(ext==='svgz'){const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));bytes=new Uint8Array(await new Response(stream).arrayBuffer());}
 const {default:DOMPurify}=await import('dompurify');
 const clean=DOMPurify.sanitize(new TextDecoder().decode(bytes),{USE_PROFILES:{svg:true,svgFilters:true},FORBID_TAGS:['foreignObject','script']});
 const doc=new DOMParser().parseFromString(clean,'image/svg+xml');
 if(doc.querySelector('parsererror'))throw new Error('Invalid SVG markup.');
 const svg=doc.documentElement;let width=parseFloat(svg.getAttribute('width')),height=parseFloat(svg.getAttribute('height'));
 const view=svg.getAttribute('viewBox')?.split(/[ ,]+/).map(Number);
 width=width||view?.[2]||1024;height=height||view?.[3]||1024;
 const scale=Math.min(1,8192/Math.max(width,height));width=Math.max(1,Math.round(width*scale));height=Math.max(1,Math.round(height*scale));
 const unsafeCSS=v=>/@import/i.test(v)||[...v.matchAll(/url\(([^)]*)\)/gi)].some(m=>!m[1].trim().replace(/^['"]|['"]$/g,'').startsWith('#'));
 for(const e of doc.querySelectorAll('*')){if(e.localName==='style'&&unsafeCSS(e.textContent))e.remove();for(const a of [...e.attributes])if(unsafeCSS(a.value)||['href','xlink:href'].includes(a.name)&&!/^#|^data:image\/(png|jpeg|webp|gif);base64,/i.test(a.value))e.removeAttribute(a.name);}
 svg.setAttribute('width',String(width));svg.setAttribute('height',String(height));
 const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(doc)],{type:'image/svg+xml'}));
 try{const img=new Image();img.src=url;await img.decode();const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;canvas.getContext('2d').drawImage(img,0,0,width,height);const blob=await new Promise(r=>canvas.toBlob(r,'image/png'));if(!blob)throw new Error('SVG rendering failed.');return new Uint8Array(await blob.arrayBuffer());}finally{URL.revokeObjectURL(url);}
}
export async function convertFile(file,route,options,onStatus,companionFiles=[]){
 const from=getFormat(route.from),to=getFormat(route.to);let bytes=new Uint8Array(await file.arrayBuffer());
 if(route.engine==='image'){
  let imageSource=from;if(['svg','svgz'].includes(from.ext)){onStatus('Rendering SVG locally…');bytes=await svgToPNG(bytes,from.ext);imageSource={coder:'PNG'};}
  const result=await image(bytes,imageSource,to.ext==='pdf'?{coder:'PNG'}:to,options,onStatus);
  let output=to.ext==='pdf'?await pdfFromImage(result.bytes,'png'):result.bytes;if(to.ext==='svgz'&&!(output[0]===31&&output[1]===139))output=gzipSync(output);return {bytes:output,ext:to.ext};
 }
 if(route.engine==='document'){
  const companions=[];for(const f of companionFiles)if(f!==file)companions.push({name:f.name.replaceAll('\\','/').split('/').pop(),bytes:new Uint8Array(await f.arrayBuffer())});
  return documentConvert(bytes,from,to,options,onStatus,companions);
 }
 if(route.engine==='pdf')return pdfConvert(bytes,to,options,onStatus);
 if(route.engine==='media')return mediaConvert(bytes,from,to,options,onStatus);
 const result=await request(getWorker('science'),{bytes,engine:route.engine,ext:from.ext,target:to.ext,options:{...options,readFormat:from.ase||from.mesh||from.bio,writeFormat:to.ase||to.mesh||to.bio}},onStatus);
 return {bytes:result.bytes,ext:to.ext};
}
