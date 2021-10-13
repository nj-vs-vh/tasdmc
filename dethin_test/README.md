This is a simple test of whether in/out file buffering helps dethinning run faster.

dethinning is run on one sample file with syscalls counted using `strace`

## How to use

1. Go to `src/extensions` and comment `#define INMEMORY_BUFFERING` line in `dethinning/main.c`, then run `make install`.

2. Go back here, change `#define OUTPUT_FILE` in `dethin.c` to `dethinning-out-nobuf` and run

```bash
. build.sh
. count_syscalls.sh
```

2. Repeat step 1, but uncomment `#define`
3. Repeat step 2, but set `#define OUTPUT_FILE dethinning-out-buf`
4. Run `. validate_outputs.sh` to make sure files are similar

## Current results

On small (11 Mb -> 35 Mb dethinned) files results are

No buffering:

```
20195 syscalls.txt

real    0m1,003s
user    0m0,943s
sys     0m0,060s
```

With buffering:

```
8940 syscalls.txt

real    0m0,959s
user    0m0,918s
sys     0m0,020s
```
