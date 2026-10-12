"""Compile a macOS CLI using this checkout's Mach-O conversion routines."""

from pathlib import Path
import subprocess

source = Path("LiveContainer/LCMachOUtils.m").read_text()
rounding = source[source.index("static uint32_t rnd32("):source.index("struct dyld_all_image_infos *")]
patching = source[source.index("static uint32_t get_chained_fixups_seg_count("):source.index("NSString *LCParseMachO(")]
prefix = r'''
#import <Foundation/Foundation.h>
#include <mach-o/loader.h>
#include <mach-o/fixup-chains.h>
#include <assert.h>
#include <libgen.h>
#define PATCH_EXEC_RESULT_SEG_COUNT_MISMATCH 1
#define PATCH_EXEC_RESULT_NO_SPACE_FOR_TWEAKLOADER 2
'''
main = r'''
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 3) return 1;
        NSError *error = nil;
        NSMutableData *data = [NSMutableData dataWithContentsOfFile:@(argv[1])
                                                           options:0 error:&error];
        if (!data || data.length < sizeof(struct mach_header_64)) {
            NSLog(@"Cannot read executable: %@", error);
            return 1;
        }
        struct mach_header_64 *header = data.mutableBytes;
        if (header->magic != MH_MAGIC_64 || header->cputype != CPU_TYPE_ARM64) {
            NSLog(@"Expected a thin arm64 Mach-O executable");
            return 1;
        }
        int result = LCPatchExecSlice(argv[2], header, false);
        if (result & PATCH_EXEC_RESULT_SEG_COUNT_MISMATCH) return 1;
        if (![data writeToFile:@(argv[2]) options:NSDataWritingAtomic error:&error]) {
            NSLog(@"Cannot write dylib: %@", error);
            return 1;
        }
        return 0;
    }
}
'''
Path("dylibify.m").write_text(prefix + rounding + patching + main)
subprocess.run(["clang", "dylibify.m", "-fblocks", "-fobjc-arc", "-framework", "Foundation", "-o", "dylibify"], check=True)
