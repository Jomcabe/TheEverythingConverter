let py, boot;
const BASE = 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/';
const send = message => self.postMessage({type:'status',message});
async function runtime() {
 if (!boot) boot=(async()=>{
  send('Loading the scientific runtime. The first conversion downloads about 12 MB.');
  importScripts(BASE+'pyodide.js');
  py=await loadPyodide({indexURL:BASE,stdout:()=>{},stderr:()=>{}});
  await py.loadPackage(['micropip','lzma']);
  const response=await fetch(new URL('scientific.py',self.location.href));
  if(!response.ok)throw new Error('Could not load scientific conversion code.');
  await py.runPythonAsync(await response.text());return py;
 })().catch(e=>{boot=null;throw e;});
 return boot;
}
async function packages(engine,ext,target) {
 const built=new Set(),pip=new Set();
 const add=(...names)=>names.forEach(x=>built.add(x));
 const install=(...names)=>names.forEach(x=>pip.add(x));
 if(engine==='table') {
  add('pandas');
  if(['xlsx','xls','xlsb','ods'].includes(ext))add('python-calamine');
  if(target==='xlsx')install('openpyxl==3.1.5');
  if(target==='ods')install('odfpy==1.4.1');
  if(ext==='parquet'||target==='parquet')add('fastparquet');
  if(ext==='html')add('lxml','beautifulsoup4');
  if(target==='md')install('tabulate==0.9.0');
  if(['sqlite','db'].includes(ext)||target==='sqlite')add('sqlite3');
 }
 if(engine==='config') {if([ext,target].some(e=>['yaml','yml'].includes(e)))add('pyyaml');if(target==='toml')add('tomli-w');if([ext,target].includes('msgpack'))add('msgpack');if([ext,target].includes('xml'))install('xmltodict==0.14.2');if([ext,target].includes('cbor'))install('cbor2==5.6.5');}
 if(['array','spectrum','atom','mesh','sequence'].includes(engine))add('numpy');
 if(engine==='array'){
  const both=[ext,target];
  if(both.some(e=>['mat','mtx'].includes(e)))add('scipy');
  if(both.some(e=>['mat','h5','hdf5','hdf'].includes(e)))add('h5py');
  if(both.some(e=>['nc','netcdf'].includes(e)))add('netcdf4');
  if(both.some(e=>['fits','fts','fit'].includes(e)))add('astropy');
 }
 if(engine==='spectrum') {
  if(['jdx','dx','jcamp'].includes(ext)){add('scipy');install('jcamp==1.3.0');}
  if(ext==='spc')install('spc-spectra==0.4.0');
 }
 if(engine==='atom'){add('scipy','matplotlib');install('ase==3.26.0');}
 if(engine==='mesh'){add('rich');install('meshio==5.3.5');}
 if(engine==='sequence')add('biopython');
 if(engine==='geo')add('shapely');
 if(engine==='font')add('fonttools','brotli');
 if(engine==='archive')add('lzma');
 if(engine==='compression')add('lzma','zstandard','brotli');
 if(built.size){send('Loading packages: '+[...built].join(', '));await py.loadPackage([...built]);}
 if(pip.size){send('Loading format readers: '+[...pip].map(x=>x.split('==')[0]).join(', '));const m=py.pyimport('micropip');try{const wheels={'jcamp==1.3.0':'jcamp-1.3.0-py3-none-any.whl','spc-spectra==0.4.0':'spc_spectra-0.4.0-py3-none-any.whl','odfpy==1.4.1':'odfpy-1.4.1-py2.py3-none-any.whl','cbor2==5.6.5':'cbor2-5.6.5-py3-none-any.whl'};if(pip.has('jcamp==1.3.0')){await py.runPythonAsync('import micropip; await micropip.install('+JSON.stringify(new URL('wheels/'+wheels['jcamp==1.3.0'],self.location.href).href)+', deps=False)');pip.delete('jcamp==1.3.0');}if(pip.size)await m.install([...pip].map(p=>wheels[p]?new URL('wheels/'+wheels[p],self.location.href).href:p));}finally{m.destroy();}}
}
self.onmessage=async({data})=>{
 let dir;
 try{
  await runtime();await packages(data.engine,data.ext,data.target);
  dir='/job-'+Date.now();py.FS.mkdir(dir);
  const src=dir+'/input.'+data.ext,dst=dir+'/output.'+data.target;
  py.FS.writeFile(src,new Uint8Array(data.bytes));
  py.globals.set('_src',src);py.globals.set('_dst',dst);py.globals.set('_engine',data.engine);py.globals.set('_ext',data.ext);py.globals.set('_target',data.target);py.globals.set('_opts_json',JSON.stringify(data.options));
  send('Converting your file locally…');
  await py.runPythonAsync('convert(_src,_dst,_engine,_ext,_target,json.loads(_opts_json))');
  const output=py.FS.readFile(dst);self.postMessage({type:'result',bytes:output},[output.buffer]);
 }catch(e){self.postMessage({type:'error',message:String(e.message||e).split('\n').slice(-8).join('\n')});}
 finally{if(py&&dir){try{await py.runPythonAsync(`shutil.rmtree(${JSON.stringify(dir)},ignore_errors=True)`);}catch{}}}
};
