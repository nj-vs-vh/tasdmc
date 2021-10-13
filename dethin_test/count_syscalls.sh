# strace -e trace=%desc --trace-path=./dethinning-out -o syscalls.txt ./dethin
strace -e trace=%desc -o syscalls.txt ./dethin
wc -l syscalls.txt

time ./dethin
