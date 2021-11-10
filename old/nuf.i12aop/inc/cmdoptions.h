/******************************  CLASS FOR HANDLING THE PROGRAM ARGUMENTS ********************************************/

#include <map>
#include <string>


typedef std::map<std::string, std::string> TStrStrMap;
typedef std::pair<std::string, std::string> TStrStrPair;


class CmdOptions
{
 public:
  TStrStrMap opt;
  bool getFromCmdLine(int argc, char **argv);
  void printOpts(); // print out the arguments
  bool isset(std::string key);
  std::string get(std::string key);
  
  CmdOptions();
  ~CmdOptions();
};



/********************************************************************************************************************/
