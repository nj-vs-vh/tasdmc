/******************************** CLASS FOR HANDLING SD RUN DST FILES ************************************************/

class SDrunClass
{

 public:
    
  bool openDSTfile(char *dInFile);
  bool readEvent();      // to read next event in the DST file
  void closeDSTfile(); 
  
    
  SDrunClass();
  ~SDrunClass();

  // private:  
  integer4           // To read the DST files    
    rc,
    wantBanks,
    gotBanks,
    size,
    inUnit,
    inMode,
    event;
};


/********************************************************************************************************************/
