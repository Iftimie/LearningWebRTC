sudo apt update
sudo apt install -y build-essential cmake pkg-config libssl-dev libusrsctp-dev libcurl4-openssl-dev
cd ~
git clone https://github.com/paullouisageneau/libdatachannel.git
cd libdatachannel
git submodule update --init --recursive
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_SYSTEM_SRTP=OFF -DUSE_SYSTEM_USRSCTP=OFF
make -j$(nproc)
sudo make install
sudo ldconfig



g++ offerer.cpp  -o offerer  -std=c++17 -I/usr/local/include -L/usr/local/lib   -ldatachannel -lpthread -lssl -lcrypto -ldl
g++ answerer.cpp -o answerer -std=c++17 -I/usr/local/include -L/usr/local/lib   -ldatachannel -lpthread -lssl -lcrypto -ldl


g++ offerer_manual.cpp  -o offerer  -std=c++17 -I/usr/local/include -L/usr/local/lib   -ldatachannel -lpthread -lssl -lcrypto -ldl
g++ answerer_manual.cpp -o answerer -std=c++17 -I/usr/local/include -L/usr/local/lib   -ldatachannel -lpthread -lssl -lcrypto -ldl

# Terminal 1
STUN=stun:stun.l.google.com:19302 ./offerer
# Terminal 2
STUN=stun:stun.l.google.com:19302 ./answerer


# Terminal 1
STUN= ./offerer
# Terminal 2
STUN= ./answerer




