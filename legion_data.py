"""Legion.bin uses LID_ identifiers independently of Growth learning tables."""
EXPECTED={0x20:('string',8),0x28:('string',8),
 **{offset:('u8',1) for offset in (0x30,0x31,0x32,0x33,0x9a,0x9b)},
 **{offset:('u16',2) for offset in (0x34,0x98)},
 0x38:('data',16),0x48:('data[]',16),0x58:('data[]',16),0x68:('string',8),
 **{offset:('s16',2) for offset in range(0x70,0x86,2)},
 0x88:('string[]',16),0xa0:('string[]',16),0xb0:('data',16)}


def create_model(EditableTable,DataError):
    class Legion(EditableTable):
        group_name='軍団兵';layout=(192,28);prefix='LID_';filename='Legion.bin';project_format='fw-legion-edits-v1'
        def __init__(self,raw):
            super().__init__(raw)
            if {f.offset:(f.kind,f.size) for f in self.fields}!=EXPECTED:raise DataError('Unsupported Legion.bin field layout.')
            for row in self.records:
                for field in self.fields:self.original(row,field)
        def project(self):return {**super().project(),'source_file':self.filename}
        def load_project(self,project):
            if project.get('source_file')!=self.filename:raise DataError('Legion project belongs to a different source file.')
            super().load_project(project)
    return Legion
