import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import catalog,ci,publish

class PublishingChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.names=[publish.PACKAGE+'-win.zip',publish.PACKAGE+'-linux.tar.bz2',publish.VERSION+'离线全文.html','verification-evidence.zip','save-baseline.zip']
        lines=[]
        for name in self.names:
            data=('isolated-unit-fixture:'+name).encode();(self.root/name).write_bytes(data);lines.append(hashlib.sha256(data).hexdigest()+'  '+name)
        (self.root/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
        self.patcher=patch.object(publish,'DIST',self.root);self.patcher.start();self.addCleanup(self.patcher.stop)
    def test_tampered_release_is_rejected(self):
        (self.root/self.names[0]).write_text('tampered')
        with self.assertRaises(SystemExit):publish.verified_files()
    def test_manifest_cannot_upload_arbitrary_files(self):
        with (self.root/'SHA256SUMS.txt').open('a') as f:f.write('0'*64+'  ../private.env\n')
        with self.assertRaises(SystemExit):publish.verified_files()
    def test_dry_run_never_contacts_github(self):
        from types import SimpleNamespace
        with patch.object(publish,'api',side_effect=AssertionError('network forbidden')),contextlib.redirect_stdout(io.StringIO()):
            publish.github(SimpleNamespace(tag='v'+publish.VERSION,dry_run=True,draft=True))
    def test_version_mismatch_is_rejected(self):
        with self.assertRaises(SystemExit):ci.tag('v999.999')
    def test_itch_target_cannot_inject_channel(self):
        from types import SimpleNamespace
        with self.assertRaises(SystemExit):publish.itch(SimpleNamespace(target='user/game:other-channel',dry_run=True))

class BodyChecks(unittest.TestCase):
    def test_unregistered_padding_is_not_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'game/data').mkdir(parents=True);(root/'game/story').mkdir()
            (root/'game/data/chapters.json').write_text(json.dumps({'g01':{'title':'first'}}))
            (root/'game/story/test.rpy').write_text('label g01:\n    return\nlabel unreachable_padding:\n    "不能拿这段凑正式字数。"\n    return\n')
            with patch.object(catalog,'ROOT',root),patch.object(catalog,'GAME',root/'game'):
                _,report,rows=catalog.scan()
            self.assertEqual(report['total'],0);self.assertEqual(rows,[]);self.assertEqual(report['unexpected_labels'],['unreachable_padding'])

if __name__=='__main__':unittest.main()
