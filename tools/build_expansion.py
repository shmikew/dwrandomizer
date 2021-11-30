#!/usr/bin/env python3

from glob import glob
from subprocess import run
from os.path import dirname, basename, realpath, join, exists
from os import chdir, remove, getcwd
from distutils.spawn import find_executable

from ips import Patch


def generate_header():
    print("Generating header file...")
    with open('../common/expansion.h', 'w') as h, open('credits.lua', 'r') as f:
        h.write(f'/** This file is generated by {basename(__file__)} */\n')
        h.write('#ifndef _EXPANSION_H_\n')
        h.write('#define _EXPANSION_H_\n')
        h.write('\n')
        h.write('#include "dwr_types.h"\n')
        h.write('\n')
        h.write('enum hooktype {\n')
        h.write('    DIALOGUE,\n')
        h.write('    JSR = 0x20,\n')
        h.write('    JMP = 0x4c,\n')
        h.write('};\n')
        h.write('\n')
        h.write('enum subroutine {\n')
        for entry in f:
            k,v = [x.strip() for x in entry.split('=')]
            if not k[0].isalpha():
                continue
            v = int(v, 16)
            if (0xc288 <= v < 0xf35b):
                h.write(f'  {k.upper()} = 0x{v:X},\n')
        h.write('};\n')
        h.write('\n')
        h.write('void add_hook(dw_rom *rom, enum hooktype type, uint16_t address,\n')
        h.write('        enum subroutine to_addr);\n')
        h.write('void bank_3_patch(dw_rom *rom);\n')
        h.write('void fill_expansion(dw_rom *rom);\n')
        h.write('\n')
        h.write('#endif\n')

def generate_c_file(b3_patch:bytes, expansion:bytes):
    print("Generating C file...")
    with open('../common/expansion.c', 'w') as c:
        c.write(f'/** This file is generated by {basename(__file__)} */\n')
        c.write(f'/** Assembly source available in the expansion directory */\n\n')
        c.write('#include <stdint.h>\n')
        c.write('#include <stddef.h>\n')
        c.write('#include "expansion.h"\n')
        c.write('#include "credit_music.h"\n')
        c.write('#include "dwr_types.h"\n')
        c.write('#include "patch.h"\n')
        c.write('\n')
        c.write('void add_hook(dw_rom *rom, enum hooktype type, uint16_t address,\n')
        c.write('        enum subroutine to_addr)\n')
        c.write('{\n')
        c.write('    switch(type) {\n')
        c.write('        case DIALOGUE:\n')
        c.write('            vpatch(rom, address, 4, 0x20, to_addr & 0xff, to_addr >> 8, 0xea);\n')
        c.write('            break;\n')
        c.write('        case JSR:\n')
        c.write('        case JMP:\n')
        c.write('            vpatch(rom, address, 3, type, to_addr & 0xff, to_addr >> 8);\n')
        c.write('            break;\n')
        c.write('        default:\n')
        c.write('            break;\n')
        c.write('    }\n')
        c.write('}\n')
        c.write('\n')
        c.write('void bank_3_patch(dw_rom *rom)\n')
        c.write('{\n')
        empty = [0xff] * len(b3_patch)
        p = Patch.create(empty, b3_patch)
        for r in p.records:
            c.write(f'    vpatch(rom, 0x{r.address+0xc288:04x},'
                    f'{len(r.content):4d},')
            for i,b in enumerate(r.content):
                if i:
                    c.write(',')
                if not i % 12:
                    c.write('\n       ')
                c.write(f' 0x{b:02x}')
            c.write('\n    );\n')
        c.write('}\n\n')

        c.write('void fill_expansion(dw_rom *rom)\n')
        c.write('{\n')
        empty = [0xff] * len(expansion)
        p = Patch.create(empty, expansion)
        for r in p.records:
            if r.address == 0x4000:
                continue  # single byte placeholder for music, ignore it
            c.write(f'    pvpatch(&rom->expansion[0x{r.address:04x}],'
                    f'{len(r.content):4d},')
            for i,b in enumerate(r.content):
                if i:
                    c.write(',')
                if not i % 12:
                    c.write('\n       ')
                c.write(f' 0x{b:02x}')
            c.write('\n    );\n')
        c.write('}\n\n')

def main():
    chdir(join(dirname(realpath(__file__)), '..', 'expansion'))
    asm6 = find_executable('asm6f') or find_executable('asm6')
    if run([asm6, '-q', '-f', '-dDWR_BUILD', 'credits.asm', 'credits.nes']
            ).returncode:
        return -1

    with open('credits.nes', 'rb') as f:
        f.seek(0xc000 + 16)
        expansion= f.read(0x10000)
        f.seek(0x1c288 + 16)
        b3_patch = f.read(0xf35b - 0xc288)
    generate_header()
    generate_c_file(b3_patch, expansion)
    remove('credits.nes')
    remove('credits.lua')

if __name__ == "__main__":
    main()
