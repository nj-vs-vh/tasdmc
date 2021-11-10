#include "nuf.h"
/************************** CLASS FOR HANDLING SD PASS0 DST FILES ***************************************************/

SDrunClass::SDrunClass()
{
  // This parameters are set globally in the class.  They are needed for reading the DST files.
  
  // for events

  // if we want to read all banks
  // size = 512;
  // wantBanks = newBankList(size)
  // eventAllBanks(wantBanks)

  size = 100;
  inUnit = 2;
  inMode = MODE_READ_DST;
  wantBanks = newBankList(size);
  addBankList(wantBanks, RUSDRAW_BANKID);
  addBankList(wantBanks, RUSDMC_BANKID);
  addBankList(wantBanks, RUSDMC1_BANKID);
  addBankList(wantBanks, TASDCALIBEV_BANKID);
  addBankList(wantBanks, RUFPTN_BANKID);
  addBankList(wantBanks, RUSDGEOM_BANKID);
  addBankList(wantBanks, RUFLDF_BANKID);
  gotBanks = newBankList(size);
}

SDrunClass::~SDrunClass() {}


bool SDrunClass::openDSTfile(char *dInFile)
{
  bool success_flag;

  success_flag = true;

  // open event DST file which contains the pass1 banks
  
  if((rc=dstOpenUnit(inUnit, dInFile, inMode)) < 0 ) 
    {
      fprintf(stderr, "Can't open %s\n",dInFile);
      success_flag = false;
    }  
  printf("Opened DST file: %s\n", dInFile);
  
  return success_flag; 
}


bool SDrunClass::readEvent()
{
  rc = eventRead (inUnit, wantBanks, gotBanks, &event); 
  if(rc < 0)
    { 
      return false;  // Can't read any more events, at the end of the file.
    }
  return true;
}


void SDrunClass::closeDSTfile()
{
  dstCloseUnit(inUnit);
}


/********************************************************************************************************************/
