"""Browser conversion engines. No subprocesses, uploaded files, or pickle loading."""
import io, os, json, csv, re, pathlib, shutil, tempfile, zipfile, tarfile, gzip, bz2, lzma
MAX_EXPANDED = 256 * 1024 * 1024

def safe_name(name):
    p = pathlib.PurePosixPath(name.replace('\\','/'))
    if p.is_absolute() or '..' in p.parts or (p.parts and ':' in p.parts[0]):
        raise ValueError('Archive contains an unsafe path.')
    return str(p)

def convert(src, dst, engine, ext, target, opts):
    if engine == 'table': return table(src,dst,ext,target,opts)
    if engine == 'config': return config(src,dst,ext,target)
    if engine == 'array': return array(src,dst,ext,target,opts)
    if engine == 'spectrum': return spectrum(src,dst,ext,target)
    if engine == 'atom': return atom(src,dst,opts)
    if engine == 'mesh': return mesh(src,dst,opts)
    if engine == 'sequence': return sequence(src,dst,opts)
    if engine == 'geo': return geo(src,dst,ext,target)
    if engine == 'font': return font(src,dst,target)
    if engine == 'archive': return archive(src,dst,ext,target)
    if engine == 'compression': return compression(src,dst,ext,target)
    raise ValueError('Unknown conversion engine.')

def table(src,dst,ext,target,opts):
    import pandas as pd
    sheet=opts.get('dataset','').strip()
    if ext in ('csv','tsv'):
        kw={'sep':'\t' if ext=='tsv' else opts.get('delimiter',',') or ','}
        df=pd.read_csv(src,**kw)
    elif ext in ('xlsx','xls','xlsb','ods'):
        sheet=int(sheet) if sheet.isdigit() else sheet or 0
        df=pd.read_excel(src,sheet_name=sheet,engine='calamine')
    elif ext in ('json','jsonl','ndjson'):
        df=pd.read_json(src,lines=ext!='json')
    elif ext=='parquet': df=pd.read_parquet(src,engine='fastparquet')
    elif ext=='dta': df=pd.read_stata(src)
    elif ext in ('sas7bdat','xpt'): df=pd.read_sas(src,format=ext,encoding='utf-8')
    elif ext=='xml': df=pd.read_xml(src,parser='etree')
    elif ext=='html': df=pd.read_html(src)[0]
    elif ext in ('sqlite','db'):
        import sqlite3
        with sqlite3.connect(f'file:{src}?mode=ro',uri=True) as c:
            tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            if not tables: raise ValueError('No tables found in this database.')
            selected=sheet or tables[0]
            if selected not in tables: raise ValueError('Choose a table: '+', '.join(tables))
            df=pd.read_sql_query('SELECT * FROM "'+selected.replace('"','""')+'"',c)
    else: raise ValueError('Unsupported table input.')
    if target=='csv': df.to_csv(dst,index=False)
    elif target=='tsv': df.to_csv(dst,sep='\t',index=False)
    elif target=='json': df.to_json(dst,orient='records',indent=2,date_format='iso')
    elif target=='jsonl': df.to_json(dst,orient='records',lines=True,date_format='iso')
    elif target=='xlsx': df.to_excel(dst,index=False,engine='openpyxl')
    elif target=='ods': df.to_excel(dst,index=False,engine='odf')
    elif target=='parquet':
        df.columns=df.columns.map(str)
        df.to_parquet(dst,index=False,engine='fastparquet')
    elif target=='html': df.to_html(dst,index=False,escape=True)
    elif target=='md': pathlib.Path(dst).write_text(df.to_markdown(index=False))
    elif target=='xml': df.to_xml(dst,index=False,parser='etree')
    elif target=='sqlite':
        import sqlite3
        with sqlite3.connect(dst) as c: df.to_sql('data',c,index=False)
    else: raise ValueError('Unsupported table output.')

def config(src,dst,ext,target):
    import tomllib, plistlib, configparser
    if ext in ('yaml','yml') or target in ('yaml','yml'):import yaml
    if target=='toml':import tomli_w
    if ext=='xml' or target=='xml':import xmltodict
    if ext=='msgpack' or target=='msgpack':import msgpack
    if ext=='cbor' or target=='cbor':import cbor2
    raw=pathlib.Path(src).read_bytes()
    if ext=='json': data=json.loads(raw)
    elif ext in ('yaml','yml'): data=yaml.safe_load(raw)
    elif ext=='toml': data=tomllib.loads(raw.decode())
    elif ext=='xml': data=xmltodict.parse(raw,disable_entities=True)
    elif ext=='plist': data=plistlib.loads(raw)
    elif ext=='msgpack': data=msgpack.unpackb(raw,raw=False,strict_map_key=False)
    elif ext=='cbor': data=cbor2.loads(raw)
    elif ext=='ini':
        c=configparser.ConfigParser(interpolation=None); c.read_string(raw.decode());data={s:dict(c[s]) for s in c.sections()}
    if target=='json': pathlib.Path(dst).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False))
    elif target in ('yaml','yml'): pathlib.Path(dst).write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False))
    elif target=='toml': pathlib.Path(dst).write_text(tomli_w.dumps(data))
    elif target=='xml': pathlib.Path(dst).write_text(xmltodict.unparse(data if isinstance(data,dict) and len(data)==1 else {'root':data},pretty=True))
    elif target=='plist': pathlib.Path(dst).write_bytes(plistlib.dumps(data))
    elif target=='msgpack': pathlib.Path(dst).write_bytes(msgpack.packb(data,use_bin_type=True))
    elif target=='cbor': pathlib.Path(dst).write_bytes(cbor2.dumps(data))
    elif target=='ini':
        if not isinstance(data,dict) or not all(isinstance(v,dict) for v in data.values()): raise ValueError('INI needs an object containing sections, each with key/value pairs.')
        c=configparser.ConfigParser(interpolation=None);c.read_dict(data)
        with open(dst,'w') as f:c.write(f)

def pick(items,name):
    choices={str(k):v for k,v in items.items() if not str(k).startswith('__')}
    if not choices: raise ValueError('No numeric datasets found.')
    if name and name not in choices: raise ValueError('Available datasets: '+', '.join(choices))
    return choices[name or next(iter(choices))]

def read_array(src,ext,opts):
    import numpy as np
    name=opts.get('dataset','').strip()
    if ext=='npy': return np.load(src,allow_pickle=False)
    if ext=='npz':
        with np.load(src,allow_pickle=False) as z:return pick(dict(z),name)
    if ext in ('h5','hdf5','hdf'):
        import h5py
        with h5py.File(src,'r') as f:
            data={};f.visititems(lambda k,v:data.update({k:v}) if isinstance(v,h5py.Dataset) else None)
            return np.asarray(pick(data,name)[()])
    if ext=='mat':
        import scipy.io, h5py
        if h5py.is_hdf5(src):
            with h5py.File(src,'r') as f:
                data={};f.visititems(lambda k,v:data.update({k:v}) if isinstance(v,h5py.Dataset) else None)
                return np.asarray(pick(data,name)[()]).T
        return np.asarray(pick(scipy.io.loadmat(src),name))
    if ext in ('nc','netcdf'):
        import netCDF4
        with netCDF4.Dataset(src) as f:return np.asarray(pick({k:v[:] for k,v in f.variables.items()},name))
    if ext in ('fits','fts','fit'):
        from astropy.io import fits
        with fits.open(src,memmap=False) as f:return np.asarray(pick({str(i):h.data for i,h in enumerate(f) if h.data is not None},name))
    if ext=='mtx':
        from scipy.io import mmread
        a=mmread(src);return a.toarray() if hasattr(a,'toarray') else np.asarray(a)
    delim=opts.get('delimiter','')
    if ext=='csv': delim=delim or ','
    elif ext=='tsv':delim='\t'
    else:delim=delim or None
    skip=int(opts.get('skipRows',0) or 0)
    return np.loadtxt(src,delimiter=delim,skiprows=skip,ndmin=2)

def write_array(data,dst,target):
    import numpy as np
    a=np.asarray(data)
    if a.dtype.hasobject: raise ValueError('Object arrays are not supported. Use numeric arrays without pickle payloads.')
    if target in ('csv','tsv'):
        if a.dtype.names: a=np.column_stack([a[n] for n in a.dtype.names])
        flat=a.reshape(1,1) if a.ndim==0 else a.reshape(-1,1) if a.ndim==1 else a.reshape(a.shape[0],-1)
        np.savetxt(dst,flat,delimiter=',' if target=='csv' else '\t',fmt='%s')
    elif target=='json':
        def normalize(v):
            if isinstance(v,complex):return {'real':v.real,'imag':v.imag}
            if isinstance(v,bytes):return v.decode('utf-8',errors='replace')
            raise TypeError('This array contains data that JSON cannot represent.')
        pathlib.Path(dst).write_text(json.dumps(a.tolist(),indent=2,default=normalize,allow_nan=False))
    elif target=='npy': np.save(dst,a,allow_pickle=False)
    elif target=='npz': np.savez_compressed(dst,data=a)
    elif target=='mat':
        from scipy.io import savemat
        savemat(dst,{'data':a})
    elif target=='h5':
        import h5py
        with h5py.File(dst,'w') as f:f.create_dataset('data',data=a)
    elif target=='nc':
        import netCDF4
        if a.dtype.kind not in 'biuf':raise ValueError('NetCDF output requires a real numeric array.')
        with netCDF4.Dataset(dst,'w',format='NETCDF4') as f:
            dims=[]
            for i,n in enumerate(a.shape):
                d='dim_'+str(i);f.createDimension(d,n);dims.append(d)
            v=f.createVariable('data','f8',tuple(dims));v[:]=a
    elif target=='fits':
        from astropy.io import fits
        fits.PrimaryHDU(a).writeto(dst,overwrite=True)
    elif target=='mtx':
        from scipy.io import mmwrite
        if a.ndim!=2: raise ValueError('Matrix Market requires a two-dimensional numeric array.')
        mmwrite(dst,a)
    else:raise ValueError('Unsupported scientific output.')

def array(src,dst,ext,target,opts):write_array(read_array(src,ext,opts),dst,target)

def spectrum(src,dst,ext,target):
    import numpy as np
    if ext in ('jdx','dx','jcamp'):
        from jcamp import jcamp_readfile
        d=jcamp_readfile(src)
        if 'x' not in d or 'y' not in d:raise ValueError('This JCAMP file has no single XY spectrum.')
        x,y=np.asarray(d['x']),np.asarray(d['y'])
    elif ext=='spa':
        # Common OMNIC directory records: type 2 = spectral header, type 3 = float data.
        import struct
        b=pathlib.Path(src).read_bytes();header=None;payload=None
        if not b.startswith(b'Spectral Data File') or len(b)<304:raise ValueError('Unsupported OMNIC SPA file signature.')
        count=struct.unpack_from('<H',b,294)[0]
        for offset in range(304,min(len(b)-16,304+count*16),16):
            kind=struct.unpack_from('<H',b,offset)[0];start,size=struct.unpack_from('<II',b,offset+2)
            if start<=0 or start+size>len(b):continue
            if kind==2:header=start
            if kind==3:payload=(start,size)
        if header is None or payload is None:raise ValueError('Unsupported OMNIC SPA layout. Export JCAMP-DX or CSV from OMNIC for this file.')
        n=struct.unpack_from('<I',b,header+4)[0];first,last=struct.unpack_from('<ff',b,header+16)
        if n<2 or n>payload[1]//4 or not np.isfinite([first,last]).all():raise ValueError('Invalid or unsupported OMNIC SPA spectral header.')
        y=np.frombuffer(b,dtype='<f4',count=n,offset=payload[0]).copy();x=np.linspace(first,last,n)
    elif ext=='spc':
        import spc_spectra as spc
        d=spc.File(src)
        if not d.sub:raise ValueError('No spectrum found in this SPC file.')
        x,y=np.asarray(d.x),np.asarray(d.sub[0].y)
    elif ext=='xrdml':
        import xml.etree.ElementTree as ET
        root=ET.parse(src).getroot()
        scans=[e for e in root.iter() if e.tag.split('}')[-1]=='scan']
        root=scans[0] if scans else root
        one=lambda tag:[e for e in root.iter() if e.tag.split('}')[-1]==tag]
        intens=one('intensities') or one('counts')
        if not intens:raise ValueError('No intensities or counts in this XRDML file.')
        y=np.fromstring(intens[0].text or '',sep=' ')
        positions=one('positions');pos=next((p for p in positions if p.get('axis','').lower() in ('2theta','2 theta')),positions[0] if positions else None)
        if pos is None:raise ValueError('No scan position data.')
        vals={e.tag.split('}')[-1]:e.text for e in pos}
        x=np.fromstring(vals['listPositions'],sep=' ') if 'listPositions' in vals else np.linspace(float(vals['startPosition']),float(vals['endPosition']),len(y))
    else:
        text=pathlib.Path(src).read_text(errors='replace')
        if ext=='ras':
            m=re.search(r'\*RAS_INT_START\s*(.*?)\*RAS_INT_END',text,re.S)
            if not m:raise ValueError('No RAS intensity block found.')
            text=m.group(1)
        lines=[s for s in text.splitlines() if s.strip() and not s.lstrip().startswith(('#','*',';'))]
        points=[]
        for line in lines:
            try:
                vals=[float(v) for v in re.split(r'[,;\s]+',line.strip())]
                if len(vals)>=2:points.append(vals[:3])
            except ValueError:continue
        if not points:raise ValueError('No numeric X/Y rows found.')
        x,y=np.array([p[:2] for p in points]).T
    if len(x)!=len(y) or not len(x):raise ValueError('Spectrum X/Y lengths do not match.')
    data=np.column_stack((x,y))
    if target=='jdx':
        with open(dst,'w') as f:
            f.write('##TITLE=Converted spectrum\n##JCAMP-DX=5.01\n##DATA TYPE=XY DATA\n##XUNITS=ARBITRARY UNITS\n##YUNITS=ARBITRARY UNITS\n##XFACTOR=1\n##YFACTOR=1\n##NPOINTS='+str(len(x))+'\n##XYPOINTS=(XY..XY)\n')
            for a,b in data:f.write(f'{a:.12g}, {b:.12g}\n')
            f.write('##END=\n')
    elif target=='xy':np.savetxt(dst,data,fmt='%.12g')
    elif target in ('csv','tsv'):np.savetxt(dst,data,delimiter=',' if target=='csv' else '\t',header='x,y' if target=='csv' else 'x\ty',comments='')
    elif target=='json':pathlib.Path(dst).write_text(json.dumps({'x':x.tolist(),'y':y.tolist()},indent=2))
    else:write_array(data,dst,target)

def atom(src,dst,opts):
    import ase.io
    atoms=ase.io.read(src,format=opts['readFormat'],index=0)
    ase.io.write(dst,atoms,format=opts['writeFormat'])

def mesh(src,dst,opts):
    import meshio
    m=meshio.read(src,file_format=opts['readFormat'])
    kw={'data_format':'XML'} if opts['writeFormat']=='xdmf' else {}
    meshio.write(dst,m,file_format=opts['writeFormat'],**kw)

def sequence(src,dst,opts):
    from Bio import SeqIO
    records=list(SeqIO.parse(src,opts['readFormat']))
    if not records:raise ValueError('No sequences found.')
    if opts['writeFormat'] in ('genbank','embl','nexus'):
        for r in records:
            r.annotations.setdefault('molecule_type','DNA' if set(str(r.seq).upper())<=set('ACGTUNRYKMSWBDHV-?') else 'protein')
    SeqIO.write(records,dst,opts['writeFormat'])

def geo(src,dst,ext,target):
    import xml.etree.ElementTree as ET
    from shapely.geometry import shape,mapping,Point,LineString,Polygon
    from shapely import wkt
    def feature(g,props=None):return {'type':'Feature','geometry':mapping(g),'properties':props or {}}
    if ext in ('json','geojson'):
        d=json.loads(pathlib.Path(src).read_text())
        fs=d['features'] if d.get('type')=='FeatureCollection' else [d] if d.get('type')=='Feature' else [feature(shape(d))]
    elif ext=='wkt':fs=[feature(wkt.loads(s)) for s in pathlib.Path(src).read_text().splitlines() if s.strip()]
    elif ext=='csv':
        with open(src) as f:
            rows=list(csv.DictReader(f));fs=[]
            for r in rows:
                lat=next((r[k] for k in r if k.lower() in ('latitude','lat')),None);lon=next((r[k] for k in r if k.lower() in ('longitude','lon','lng')),None)
                if lat is None or lon is None:raise ValueError('CSV needs latitude and longitude columns.')
                fs.append(feature(Point(float(lon),float(lat)),r))
    elif ext=='gpx':
        root=ET.parse(src).getroot();fs=[]
        for e in root.iter():
            tag=e.tag.split('}')[-1]
            if tag=='wpt':fs.append(feature(Point(float(e.attrib['lon']),float(e.attrib['lat']))))
            if tag in ('trkseg','rte'):
                pts=[(float(p.attrib['lon']),float(p.attrib['lat'])) for p in e if 'lat' in p.attrib]
                if len(pts)>1:fs.append(feature(LineString(pts)))
    elif ext=='kml':
        root=ET.parse(src).getroot();fs=[]
        for e in root.iter():
            tag=e.tag.split('}')[-1]
            if tag not in ('Point','LineString','Polygon'):continue
            c=next((x for x in e.iter() if x.tag.split('}')[-1]=='coordinates'),None)
            if c is None:continue
            pts=[tuple(map(float,s.split(',')[:2])) for s in (c.text or '').split()]
            if pts:fs.append(feature(Point(pts[0]) if tag=='Point' else LineString(pts) if tag=='LineString' else Polygon(pts)))
    if not fs:raise ValueError('No supported geometries found.')
    if target in ('geojson','json'):pathlib.Path(dst).write_text(json.dumps({'type':'FeatureCollection','features':fs},indent=2))
    elif target=='wkt':pathlib.Path(dst).write_text('\n'.join(shape(f['geometry']).wkt for f in fs))
    elif target=='csv':
        with open(dst,'w',newline='') as f:
            w=csv.writer(f);w.writerow(['longitude','latitude'])
            for feat in fs:
                g=shape(feat['geometry'])
                if g.geom_type!='Point':raise ValueError('CSV export supports points only. Choose GeoJSON, WKT, or KML for lines/polygons.')
                w.writerow([g.x,g.y])
    elif target=='gpx':
        root=ET.Element('gpx',version='1.1',creator='Everything Converter',xmlns='http://www.topografix.com/GPX/1/1')
        for f in fs:
            g=shape(f['geometry'])
            if g.geom_type=='Point':ET.SubElement(root,'wpt',lat=str(g.y),lon=str(g.x))
            elif g.geom_type=='LineString':
                seg=ET.SubElement(ET.SubElement(root,'trk'),'trkseg')
                for lon,lat,*_ in g.coords:ET.SubElement(seg,'trkpt',lat=str(lat),lon=str(lon))
            else:raise ValueError('GPX export supports points and lines only.')
        ET.ElementTree(root).write(dst,encoding='utf-8',xml_declaration=True)
    elif target=='kml':
        root=ET.Element('kml',xmlns='http://www.opengis.net/kml/2.2');doc=ET.SubElement(root,'Document')
        for f in fs:
            g=shape(f['geometry']);p=ET.SubElement(doc,'Placemark')
            if f.get('properties',{}).get('name'):ET.SubElement(p,'name').text=str(f['properties']['name'])
            if g.geom_type=='Point':node=ET.SubElement(p,'Point');coords=list(g.coords)
            elif g.geom_type=='LineString':node=ET.SubElement(p,'LineString');coords=list(g.coords)
            elif g.geom_type=='Polygon':node=ET.SubElement(ET.SubElement(ET.SubElement(p,'Polygon'),'outerBoundaryIs'),'LinearRing');coords=list(g.exterior.coords)
            else:raise ValueError('KML export supports Point, LineString, and Polygon geometries.')
            ET.SubElement(node,'coordinates').text=' '.join(','.join(map(str,c[:2])) for c in coords)
        ET.ElementTree(root).write(dst,encoding='utf-8',xml_declaration=True)

def font(src,dst,target):
    from fontTools.ttLib import TTFont
    f=TTFont(src)
    if target=='otf' and 'CFF ' not in f and 'CFF2' not in f:raise ValueError('This font has TrueType outlines. Use TTF, WOFF, or WOFF2.')
    if target=='ttf' and 'glyf' not in f:raise ValueError('This font has CFF outlines. Use OTF, WOFF, or WOFF2.')
    f.flavor=target if target in ('woff','woff2') else None
    f.save(dst)

def archive(src,dst,ext,target):
    members=[];total=0
    if ext=='zip':
        with zipfile.ZipFile(src) as z:
            if len(z.infolist())>10000:raise ValueError('Too many archive entries.')
            for e in z.infolist():
                name=safe_name(e.filename)
                if e.is_dir():continue
                if (e.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive links are unsupported.')
                total+=e.file_size
                if total>MAX_EXPANDED:raise ValueError('Expanded archive exceeds 256 MiB.')
                members.append((name,z.read(e)))
    else:
        with tarfile.open(src,'r:*') as t:
            for i,e in enumerate(t):
                if i>10000:raise ValueError('Too many archive entries.')
                name=safe_name(e.name)
                if e.isdir():continue
                if not e.isfile():raise ValueError('Only regular archive files are supported.')
                total+=e.size
                if total>MAX_EXPANDED:raise ValueError('Expanded archive exceeds 256 MiB.')
                members.append((name,t.extractfile(e).read()))
    if target=='zip':
        with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in members:z.writestr(name,data)
    else:
        mode='w:gz' if target in ('tgz','tar.gz') else 'w:bz2' if target in ('tbz2','tar.bz2') else 'w:xz' if target in ('txz','tar.xz') else 'w'
        with tarfile.open(dst,mode) as t:
            for name,data in members:
                e=tarfile.TarInfo(name);e.size=len(data);t.addfile(e,io.BytesIO(data))

def compression(src,dst,ext,target):
    import zstandard,brotli
    b=pathlib.Path(src).read_bytes()
    if ext in ('gz','bz2','xz','lzma'):
        opener={'gz':gzip.open,'bz2':bz2.open,'xz':lzma.open,'lzma':lzma.open}[ext]
        with opener(src,'rb') as f:b=f.read(MAX_EXPANDED+1)
    elif ext=='zst':
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(b)) as f:b=f.read(MAX_EXPANDED+1)
    elif ext=='br':
        d=brotli.Decompressor();pieces=[];size=0
        for i in range(0,len(b),1024):
            p=d.process(b[i:i+1024]);size+=len(p)
            if size>MAX_EXPANDED:raise ValueError('Expanded file exceeds 256 MiB.')
            pieces.append(p)
        b=b''.join(pieces)
    if len(b)>MAX_EXPANDED:raise ValueError('Expanded file exceeds 256 MiB.')
    if target=='gz':b=gzip.compress(b)
    elif target=='bz2':b=bz2.compress(b)
    elif target=='xz':b=lzma.compress(b)
    elif target=='lzma':b=lzma.compress(b,format=lzma.FORMAT_ALONE)
    elif target=='zst':b=zstandard.ZstdCompressor().compress(b)
    elif target=='br':b=brotli.compress(b)
    pathlib.Path(dst).write_bytes(b)
