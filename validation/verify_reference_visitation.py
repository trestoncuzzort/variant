from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root=Path.cwd();out=root/'validation-output';out.mkdir()
compiler=os.environ['VALIDATION_COMPILER']
fixed_sha='41050ba06762d485f9b22e2917f7c9d7274b9b9d'
original_sha='d3e821cbf49589124f0fb77ff87b757d3c47d303'
records={'scope':'Targeted reference visitation/probes/category matrix/control; not full Boost.CI.',
         'compiler':compiler,'steps':[]}
def save(): (out/'results.json').write_text(json.dumps(records,indent=2)+'\n')
def dependency(item):
    name=item['repository'].split('/')[-1];directory=root/'deps'/name;directory.mkdir(parents=True)
    with (out/('dependency-'+name+'.log')).open('w') as stream:
        for cmd in [['git','init',str(directory)],['git','-C',str(directory),'fetch','--depth=1',
                    'https://github.com/'+item['repository']+'.git',item['head']],
                    ['git','-C',str(directory),'checkout','--detach','FETCH_HEAD']]:
            subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True)
    sha=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    assert sha==item['head'],(item,sha)
    return dict(item,include=str(directory/'include'))
with ThreadPoolExecutor(max_workers=6) as pool:
    records['dependencies']=list(pool.map(dependency,json.loads((root/'validation/dependencies.json').read_text())))
for phase,sha in [('original',original_sha),('fixed',fixed_sha)]:
    assert subprocess.check_output(['git','-C',str(root/phase),'rev-parse','HEAD'],text=True).strip()==sha
records.update(original_sha=original_sha,fixed_sha=fixed_sha);save()

def execute(command,label,expected=0):
    start=time.monotonic()
    with (out/(label+'.log')).open('w') as stream:
        p=subprocess.run(list(map(str,command)),cwd=out,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
    text=(out/(label+'.log')).read_text(errors='replace')
    records['steps'].append(dict(label=label,command=list(map(str,command)),returncode=p.returncode,
                                expected=expected,seconds=time.monotonic()-start,output_tail=text[-1700:]))
    save();print(label,'exit',p.returncode,flush=True)
    assert p.returncode!=0 if expected=='failure' else p.returncode==expected,(label,text[-4000:])
    return text

def build(source,owner,label,standard='17',control=False,expected=0):
    exe=out/(label+('.exe' if os.name=='nt' else ''))
    paths=([out/'direct/include'] if control else [])+[root/owner/'include',root/'validation/boost-root']
    paths += [Path(x['include']) for x in records['dependencies']]
    if compiler=='msvc':
        cmd=['cl','/nologo','/EHsc','/std:c++'+standard,'/Zc:__cplusplus','/permissive-','/Od',
             '/DBOOST_ALL_NO_LIB','/Fo:'+str(out/(label+'.obj')),'/Fe:'+str(exe)]
        cmd+=['/I'+str(p) for p in paths]+[source]
    else:
        cmd=['g++-11' if compiler=='gcc11' else 'clang++','-std=c++'+standard,'-O1','-g','-DBOOST_ALL_NO_LIB']
        if compiler=='clang-sanitized':cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
        cmd+=['-I'+str(p) for p in paths]+[source,'-o',exe]
    return exe,execute(cmd,label+'-build',expected=expected)

minimum='14' if compiler=='msvc' else '11'
exe,text=build(root/'validation/probe.cpp','original','original-probe',standard=minimum,expected='failure')
assert 'Changer' in text and ('rvalue' in text or 'bind' in text or 'C2664' in text),text[-4000:]
exe,text=build(root/'validation/probe.cpp','fixed','fixed-probe',standard=minimum)
execute([exe],'fixed-probe-run')
for phase in ['original','fixed']:
    exe,_=build(root/'validation/category-probe.cpp',phase,'category-'+phase,standard=minimum)
    text=execute([exe],'category-'+phase+'-run',expected=4 if phase=='original' else 0)
    assert text.strip()==('0 1 2 3 0 1 0 1 2 3 2 3' if phase=='original' else '0 1 2 3 0 0 0 0 2 2 2 2'),text
fixture=root/'fixed/test/variant_reference_visit_test.cpp'
for standard in [minimum,'17']:
    exe,_=build(fixture,'fixed','regression-'+standard,standard=standard)
    text=execute([exe],'regression-'+standard+'-run');assert 'No errors detected.' in text,text
    for phase in ['original','fixed']:
        label='oracle-'+phase+'-'+standard
        exe,_=build(root/'validation/category-oracle.cpp',phase,label,standard=standard)
        data=json.loads(execute([exe],label+'-run',expected=1 if phase=='original' else 0))
        assert data['comparisons']==(84 if standard=='11' else 104),data
        assert data['mismatches']==((45 if standard=='11' else 53) if phase=='original' else 0),data
text=(root/'fixed/include/boost/variant/variant.hpp').read_text()
old='        invoke_visitor<Visitor, false> invoker(visitor_);\n        return invoker.internal_visit( operand.get(), 1L );'
assert text.count(old)==2
header=out/'direct/include/boost/variant/variant.hpp';header.parent.mkdir(parents=True)
header.write_text(text.replace(old,'        return visitor_(operand.get());'))
_,text=build(fixture,'fixed','direct-control',standard='17',control=True,expected='failure')
assert 'recursive_wrapper' in text,text[-4000:]
paths=['include/boost/variant/variant.hpp','test/variant_reference_visit_test.cpp','test/Jamfile.v2']
records['source_sha256']={p:hashlib.sha256((root/'fixed'/p).read_bytes()).hexdigest() for p in paths}
records['fixture_sha256']={p:hashlib.sha256((root/'validation'/p).read_bytes()).hexdigest()
                           for p in ['probe.cpp','category-probe.cpp','category-oracle.cpp','boost-root/boost/version.hpp']}
for phase in ['original','fixed']:
    assert not subprocess.check_output(['git','-C',str(root/phase),'status','--porcelain','--untracked-files=no'],text=True)
records['all_checks_passed']=True;save();print('Pinned original failures, fixed visitation and nested-wrapper control verified.',flush=True)
