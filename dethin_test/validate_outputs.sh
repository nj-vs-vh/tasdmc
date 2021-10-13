cmp dethinning-out-buf dethinning-out-nobuf

if [ $? -eq 0 ]; then
    echo OK
else
    echo something is wrong
fi
