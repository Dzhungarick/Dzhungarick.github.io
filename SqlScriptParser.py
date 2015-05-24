# coding: utf8

'''
.▄▄ · .▄▄▄  ▄▄▌      .▄▄ ·  ▄▄· ▄▄▄  ▪   ▄▄▄·▄▄▄▄▄     ▄▄▄· ▄▄▄· ▄▄▄  .▄▄ · ▄▄▄ .▄▄▄      
▐█ ▀. ▐▀•▀█ ██•      ▐█ ▀. ▐█ ▌▪▀▄ █·██ ▐█ ▄█•██      ▐█ ▄█▐█ ▀█ ▀▄ █·▐█ ▀. ▀▄.▀·▀▄ █·    
▄▀▀▀█▄█▌·.█▌██▪      ▄▀▀▀█▄██ ▄▄▐▀▀▄ ▐█· ██▀· ▐█.▪     ██▀·▄█▀▀█ ▐▀▀▄ ▄▀▀▀█▄▐▀▀▪▄▐▀▀▄     
▐█▄▪▐█▐█▪▄█·▐█▌▐▌    ▐█▄▪▐█▐███▌▐█•█▌▐█▌▐█▪·• ▐█▌·    ▐█▪·•▐█ ▪▐▌▐█•█▌▐█▄▪▐█▐█▄▄▌▐█•█▌    
 ▀▀▀▀ ·▀▀█. .▀▀▀      ▀▀▀▀ ·▀▀▀ .▀  ▀▀▀▀.▀    ▀▀▀     .▀    ▀  ▀ .▀  ▀ ▀▀▀▀  ▀▀▀ .▀  ▀    
 '''

# разбивает скрипт на plsql/sql блоки
class ScriptParser:
    def __init__(self):
        self.__STATES = { 'STATE_NOTHING'                : -1,
                          'STATE_BEGIN_SQL_STATEMENT'    :  0,
                          'STATE_BEGIN_STRING'           :  1,
                          'STATE_BEGIN_IGNORE'           :  2,
                          'STATE_ONE_LINE_IGNORE'        :  3,
                          'STATE_BEGIN_DELIMITER'        :  4,
                          'STATE_BEGIN_LEXEM'            :  5,
                          'STATE_BEGIN_SPACES'           :  6,
                          'STATE_BEGIN_NEWLINE_CHARACTER':  7 }

        self.__simpleSymbols = { 'CHARACTER STRING DELIMITER'         :'\'',
                                 'COMPONENT SELECTOR'                 :'.',
                                 'DIVISION OPERATOR'                  :'/',
                                 'EXPRESSION OR LIST DELIMITER(OPEN)' :'(',
                                 'EXPRESSION OR LIST DELIMITER(CLOSE)':')',
                                 'HOST VARIABLE INDICATOR'            :':',
                                 'ITEM SEPARATOR'                     :',',
                                 'MULTIPLICATION OPERATOR'            :'*',
                                 'QUOTED IDENTIFIER DELIMITER'        :'"',
                                 'EQUAL TO'                           :'=',
                                 'LESS THAN'                          :'<',
                                 'GREATER THAN'                       :'>',
                                 'REMOTE ACCESS INDICATOR'            :'@',
                                 'STATEMENT TERMINATOR'               :';',
                                 'SUBTRACTION/NEGATION OPERATOR'      :'-' }

        self.__compoundSymbols = { 'ASSIGNMENT OPERATOR'                 :':=',
                                   'ASSOCIATION OPERATOR'                :'=>',
                                   'CONCATENATION OPERATOR'              :'||',
                                   'EXPONENTIATION OPERATOR'             :'**',
                                   'LABEL DELIMITER (BEGIN)'             :'<<',
                                   'LABEL DELIMITER (END)'               :'>>',
                                   'MULTI-LINE COMMENT DELIMITER (BEGIN)':'/*',
                                   'MULTI-LINE COMMENT DELIMITER (END)'  :'*/',
                                   'RANGE OPERATOR'                      :'..',
                                   'NOT EQUAL TO'                        :['<>','!=','~=','^='],
                                   '<>NOT EQUAL TO'                      :'<>',
                                   '!=NOT EQUAL TO'                      :'!=',
                                   '~=NOT EQUAL TO'                      :'~=',
                                   '^=NOT EQUAL TO'                      :'^=',
                                   'LESS THAN OR EQUAL TO'               :'<=',
                                   'GREATER THAN OR EQUAL TO'            :'>=',
                                   'SINGLE-LINE COMMENT INDICATOR'       :'--'  }

        self.__otherSymbols = { 'SPACE'            :' ',
                                'NEWLINE CHARACTER':'\n' }

        self.__currentState  = self.__STATES['STATE_NOTHING']
        self.__currentLexem        = ''
        self.__currentChar         = ''
        self.__currentDelimiter    = ''
        self.__currentComment      = ''
        self.__currentString       = ''
        self.__currentNothing      = ''
        self.__currentPosition     = 0
        self.__currentError        = ''
        self.__lexemList           = []
        self.__SqlStatements       = []
        self.__plsqlDelimiters     = '()+-*/<>=!~^;:.\'@%,"#$&|{}?[]'
        self.__scriptText          = ''

    #  ▄▄▌  ▄▄▄ .▐▄• ▄ ▪   ▄▄·  ▄▄▄· ▄▄▌       ▄▄▄·  ▐ ▄  ▄▄▄· ▄▄▌   ▄· ▄▌.▄▄ · ▪  .▄▄ · 
    #  ██•  ▀▄.▀· █▌█▌▪██ ▐█ ▌▪▐█ ▀█ ██•      ▐█ ▀█ •█▌▐█▐█ ▀█ ██•  ▐█▪██▌▐█ ▀. ██ ▐█ ▀. 
    #  ██▪  ▐▀▀▪▄ ·██· ▐█·██ ▄▄▄█▀▀█ ██▪      ▄█▀▀█ ▐█▐▐▌▄█▀▀█ ██▪  ▐█▌▐█▪▄▀▀▀█▄▐█·▄▀▀▀█▄
    #  ▐█▌▐▌▐█▄▄▌▪▐█·█▌▐█▌▐███▌▐█ ▪▐▌▐█▌▐▌    ▐█ ▪▐▌██▐█▌▐█ ▪▐▌▐█▌▐▌ ▐█▀·.▐█▄▪▐█▐█▌▐█▄▪▐█
    #  .▀▀▀  ▀▀▀ •▀▀ ▀▀▀▀▀·▀▀▀  ▀  ▀ .▀▀▀      ▀  ▀ ▀▀ █▪ ▀  ▀ .▀▀▀   ▀ •  ▀▀▀▀ ▀▀▀ ▀▀▀▀ 

    def __GetNextSymbol(self):
        self.__currentChar = ''
        if self.__NotEndOfScript():
            self.__currentChar = self.__scriptText[self.__currentPosition:self.__currentPosition+1]
            self.__IncPosition()
            return True
        else:
            return False

    def __IncPosition(self):
        self.__currentPosition += 1

    def __DecPosition(self):
        self.__currentPosition -= 1        

    def __NotEndOfScript(self):
        return self.__currentPosition < len(self.__scriptText)

    def __IsDelimiter(self,char=None):
        char = self.__currentChar if char==None else char
        return char in self.__plsqlDelimiters

    def __IsSpace(self,char=None):
        char = self.__currentChar if char==None else char
        return char == self.__otherSymbols['SPACE']        

    def __IsNewLineChar(self,char=None):
        char = self.__currentChar if char==None else char
        return char == self.__otherSymbols['NEWLINE CHARACTER']

    def __SetCurrentState(self,state):
        self.__DecPosition()
        self.__currentState = self.__STATES[state]

    def __GetLexemsAsTextTable(self):
        output = ''
        output += '\n'+'='*121 + '\n'
        for lexem in self.__lexemList:

            if lexem[2] == 'SPACE':
                __lexem = ' '
            elif lexem[2] == 'NEWLINE CHARACTER':
                __lexem = '\\n'
            else:
                __lexem = lexem[0]
            format = '|{0:^20}|{1:^20}|{2:^40}|{3:^4}|{4:^4}|{5:^10}|{6:^10}|{7:^4}|'
            output += format.format(__lexem,lexem[1],lexem[2],lexem[3],lexem[4],lexem[5],lexem[6],lexem[7]) + '\n'
        output += '='*121 + '\n'
        return output

    '''
    Definers

    '''
    def __DefineNothing(self):
        if self.__IsNewLineChar(self.__currentNothing):
            return 'NEWLINE CHARACTER'
        
        if not self.__currentNothing:
            return 'EMPTY'

        return 'SPACE'

    def __DefineDelimiter(self):
        for key, value in self.__simpleSymbols.iteritems():
            if self.__currentDelimiter == value:
                return key
        
        if not self.__currentDelimiter:
            return 'EMPTY'
                
        return 'DELIMITER'

    def __DefineLexem(self):
        return 'LEXEM'

    '''
    Parsers

    '''
    def __ParseNothing(self):
        self.__currentNothing = ''
        while self.__GetNextSymbol():
            if self.__IsSpace():
                self.__currentNothing += self.__currentChar
            elif self.__IsNewLineChar():
                self.__SetCurrentState('STATE_BEGIN_NEWLINE_CHARACTER')
                break
            elif self.__IsDelimiter():
                self.__SetCurrentState('STATE_BEGIN_DELIMITER')
                break
            else:
                self.__SetCurrentState('STATE_BEGIN_LEXEM')
                break
    
    def __ParseNewLineCharacter(self):
        self.__currentNothing = ''
        if self.__GetNextSymbol():
            if self.__IsNewLineChar():
                self.__currentNothing = self.__otherSymbols['NEWLINE CHARACTER']
            else:
                self.__SetCurrentState('STATE_NOTHING')
    
    def __ParseDilimiter(self):
        self.__currentDelimiter = ''
        if self.__GetNextSymbol():
            if self.__IsDelimiter():
                self.__currentDelimiter = self.__currentChar
            else:
                self.__SetCurrentState('STATE_NOTHING')

    def __ParseLexem(self):
        self.__currentLexem = ''
        while self.__GetNextSymbol():
            if self.__IsSpace():
                self.__SetCurrentState('STATE_NOTHING')
                break
            elif self.__IsNewLineChar():
                self.__SetCurrentState('STATE_BEGIN_NEWLINE_CHARACTER')
                break
            elif self.__IsDelimiter():
                self.__SetCurrentState('STATE_BEGIN_DELIMITER')
                break
            else:
                self.__currentLexem += self.__currentChar 

    def __LexicalAnalysis(self):
        NotEndOfScript        = self.__NotEndOfScript
        ParseNothing          = self.__ParseNothing
        ParseDilimiter        = self.__ParseDilimiter
        ParseLexem            = self.__ParseLexem
        ParseNewLineCharacter = self.__ParseNewLineCharacter
        IncPosition           = self.__IncPosition
        GetLexemsAsTextTable  = self.__GetLexemsAsTextTable
        DefineNothing         = self.__DefineNothing
        DefineDelimiter       = self.__DefineDelimiter

        while NotEndOfScript():

            inState    = self.__currentState
            inPosition = self.__currentPosition

            if self.__currentState == self.__STATES['STATE_NOTHING']:
                ParseNothing()
                if self.__currentNothing:
                    self.__lexemList.append([self.__currentNothing,
                                             'SPACE',
                                             DefineNothing(),
                                             inState,
                                             self.__currentState,
                                             inPosition,
                                             self.__currentPosition,
                                             len(self.__currentNothing)])
            elif self.__currentState == self.__STATES['STATE_BEGIN_DELIMITER']:
                ParseDilimiter()
                if self.__currentDelimiter:
                    self.__lexemList.append([self.__currentDelimiter,
                                             'DELIMITER',
                                             DefineDelimiter(),
                                             inState,
                                             self.__currentState,
                                             inPosition,
                                             self.__currentPosition,
                                             len(self.__currentDelimiter)])
            elif self.__currentState == self.__STATES['STATE_BEGIN_LEXEM']:
                ParseLexem()
                self.__lexemList.append([self.__currentLexem,
                                         'LEXEM',
                                         'LEXEM',
                                         inState,
                                         self.__currentState,
                                         inPosition,
                                         self.__currentPosition,
                                         len(self.__currentLexem)])
            
            elif self.__currentState == self.__STATES['STATE_BEGIN_NEWLINE_CHARACTER']:
                ParseNewLineCharacter()
                if self.__currentNothing:
                    self.__lexemList.append([self.__currentNothing,
                                             'NEWLINE',
                                             DefineNothing(),
                                             inState,
                                             self.__currentState,
                                             inPosition,
                                             self.__currentPosition,
                                             len(self.__currentNothing)])
            
            else:
                IncPosition()
        
        print(GetLexemsAsTextTable())

    def __SplitStatements(self):
        for lexem in enumerate(self.__lexemList):
            pass

    #  .▄▄ ·  ▄▄· ▄▄▄  ▪   ▄▄▄·▄▄▄▄▄    ▄▄▌         ▄▄▄· ·▄▄▄▄  ▄▄▄ .▄▄▄  
    #  ▐█ ▀. ▐█ ▌▪▀▄ █·██ ▐█ ▄█•██      ██•  ▪     ▐█ ▀█ ██▪ ██ ▀▄.▀·▀▄ █·
    #  ▄▀▀▀█▄██ ▄▄▐▀▀▄ ▐█· ██▀· ▐█.▪    ██▪   ▄█▀▄ ▄█▀▀█ ▐█· ▐█▌▐▀▀▪▄▐▀▀▄ 
    #  ▐█▄▪▐█▐███▌▐█•█▌▐█▌▐█▪·• ▐█▌·    ▐█▌▐▌▐█▌.▐▌▐█ ▪▐▌██. ██ ▐█▄▄▌▐█•█▌
    #   ▀▀▀▀ ·▀▀▀ .▀  ▀▀▀▀.▀    ▀▀▀     .▀▀▀  ▀█▄▀▪ ▀  ▀ ▀▀▀▀▀•  ▀▀▀ .▀  ▀
    def LoadScript(self,scriptText):
        # инициализация объекта
        self.__init__()
        
        self.__scriptText = scriptText
        
        # здесь просто получаем список слов и разделителей
        self.__LexicalAnalysis()

        # разбиваем скрипт на блоки
        self.__SplitStatements()


ScriptParser().LoadScript('''
                          -- some text
                          declare
                            a number; -- comment
                            b varchar2(4000) := 'string''_value';
                          begin
                            /** comment2 */
                            /*  comment3 */BEGIN NULL; END;
                             
                             IF a<>0 THEN
                                NULL;
                             END IF;   
                            null;
                          end;
                          /

                          select 1 as "ONE", acc.* from daccount_dbt acc;     
                          ''')
