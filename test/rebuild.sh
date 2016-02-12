

function create() {
    ROOT=$1
    ARGS=$2
    ./create_binary.py $ARGS -o ${ROOT}test1.atr 128 256 512 1024 4096
    ./create_binary.py $ARGS -o ${ROOT}test2.atr 50*256 2*512 256 1024 256 d1 d2 d3 4096
    ./create_binary.py $ARGS -o ${ROOT}test3.atr 10*256 d1 d7 4096 d3 d5 d9 8000
    ./create_binary.py $ARGS -o ${ROOT}test4.atr 10*4096 d1 d3 d5 d7 d9 15000
    ./create_binary.py $ARGS -o ${ROOT}test5.atr 100-500,7
}

create "dos_sd_" "-f a -t s"
create "dos_ed_" "-f a -t m"
create "dos_dd_" "-f a -t d"
create "sd_sd_" "-f s -t s"
create "sd_dd_" "-f s -t d"
