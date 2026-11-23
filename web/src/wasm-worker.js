import { createPandocInstance } from '../node_modules/pandoc-wasm/src/core.js';
let pandoc,magick;
const status=message=>self.postMessage({type:'status',message});
async function pandocRuntime(){
 if(!pandoc)pandoc=(async()=>{status('Loading the document engine (about 58 MB on the first use)…');const r=await fetch('https://unpkg.com/pandoc-wasm@1.1.0/src/pandoc.wasm');if(!r.ok)throw new Error('Document engine download failed.');return createPandocInstance(await r.arrayBuffer());})().catch(e=>{pandoc=null;throw e;});
 return pandoc;
}
async function imageRuntime(){
 if(!magick)magick=(async()=>{status('Loading the image engine (about 15 MB on the first use)…');const m=await import('@imagemagick/magick-wasm');await m.initializeImageMagick(new URL('https://cdn.jsdelivr.net/npm/@imagemagick/magick-wasm@0.0.46/dist/x86/magick.wasm'));return m;})().catch(e=>{magick=null;throw e;});
 return magick;
}
self.onmessage=async({data})=>{
 try{
  if(data.engine==='image'){
   const m=await imageRuntime();status('Converting your image locally…');
   let output;
   m.ImageMagick.read(new Uint8Array(data.bytes),new m.MagickReadSettings({format:data.readCoder,frameCount:1}),image=>{image.quality=data.options.quality||92;image.write(data.coder,bytes=>{output=new Uint8Array(bytes);});});
   self.postMessage({type:'result',bytes:output},[output.buffer]);
  } else if(data.engine==='document') {
   const p=await pandocRuntime();status('Converting your document locally…');
   const files={['input.'+data.ext]:new Blob([data.bytes])};
   for(const f of data.companions||[])files[f.name]=new Blob([f.bytes]);
   const outputName='output.'+(data.target==='pdf'?'html':data.target);
   const options={from:data.from,to:data.to,'input-files':['input.'+data.ext],'output-file':outputName,standalone:true,'extract-media':'media'};
   // This engine has no network access. Input HTML is never inserted into the page.
   const result=await p.convert(options,null,files);
   const out=result.files[outputName];
   if(!out)throw new Error(result.stderr||'Document conversion produced no output.');
   const bytes=typeof out==='string'?new TextEncoder().encode(out):new Uint8Array(await out.arrayBuffer());
   const media=[];
   for(const [name,blob] of Object.entries(result.mediaFiles||{}))media.push({name,bytes:typeof blob==='string'?new TextEncoder().encode(blob):new Uint8Array(await blob.arrayBuffer())});
   self.postMessage({type:'result',bytes,media,warnings:result.warnings,stderr:result.stderr},[bytes.buffer,...media.map(f=>f.bytes.buffer)]);
  }
 }catch(e){self.postMessage({type:'error',message:String(e.message||e)});}
};
