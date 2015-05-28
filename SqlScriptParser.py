# coding: utf8

'''
.▄▄ · .▄▄▄  ▄▄▌      .▄▄ ·  ▄▄· ▄▄▄  ▪   ▄▄▄·▄▄▄▄▄     ▄▄▄· ▄▄▄· ▄▄▄  .▄▄ · ▄▄▄ .▄▄▄      
▐█ ▀. ▐▀•▀█ ██•      ▐█ ▀. ▐█ ▌▪▀▄ █·██ ▐█ ▄█•██      ▐█ ▄█▐█ ▀█ ▀▄ █·▐█ ▀. ▀▄.▀·▀▄ █·    
▄▀▀▀█▄█▌·.█▌██▪      ▄▀▀▀█▄██ ▄▄▐▀▀▄ ▐█· ██▀· ▐█.▪     ██▀·▄█▀▀█ ▐▀▀▄ ▄▀▀▀█▄▐▀▀▪▄▐▀▀▄     
▐█▄▪▐█▐█▪▄█·▐█▌▐▌    ▐█▄▪▐█▐███▌▐█•█▌▐█▌▐█▪·• ▐█▌·    ▐█▪·•▐█ ▪▐▌▐█•█▌▐█▄▪▐█▐█▄▄▌▐█•█▌    
 ▀▀▀▀ ·▀▀█. .▀▀▀      ▀▀▀▀ ·▀▀▀ .▀  ▀▀▀▀.▀    ▀▀▀     .▀    ▀  ▀ .▀  ▀ ▀▀▀▀  ▀▀▀ .▀  ▀    
 '''
import sublime
import sublime_plugin

# разбивает скрипт на plsql/sql блоки
class ScriptParser:
    def __init__(self):
        
        # select * from V$RESERVED_WORDS order by KEYWORD
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

        self.__currentState = self.__STATES['STATE_NOTHING']
        self.__currentLexem = ''
        self.__currentChar = ''
        self.__currentDelimiter = ''
        self.__currentComment = ''
        self.__currentString = ''
        self.__currentNothing = ''
        self.__currentPosition = 0
        self.__currentError = ''
        self.__currentStatement = []
        self.__statementNumber = 0
        self.__lexemList = []
        self.__SqlStatements = []
        self.__SqlTextStatements = []
        self.__plsqlDelimiters = '()+-*/<>=!~^;:.\'@%,"#$&|{}?[]'
        self.__scriptText = ''
        self.__splitStatementError = dict.fromkeys(['ErrorCode','ErrorText'])

    def __GetLexemStructRow(self):
        return dict.fromkeys(['Lexem',
                              'Lexem Class',
                              'Description',
                              'Begin State',
                              'End State',
                              'Begin Position',
                              'End Position',
                              'Length' 
                             ])

    def __GetStatementLexemRow(self):
        return dict.fromkeys(['Lexem',
                              'Type',
                              'Length' 
                             ])


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

            if lexem['Description'] == 'SPACE':
                __lexem = ' '
            elif lexem['Description'] == 'NEWLINE CHARACTER':
                __lexem = '\\n'
            else:
                __lexem = lexem['Lexem']
            format = '|{0:^20}|{1:^20}|{2:^40}|{3:^4}|{4:^4}|{5:^10}|{6:^10}|{7:^4}|'
            output += format.format(__lexem,
                                      lexem['Lexem Class'],
                                      lexem['Description'],
                                      lexem['Begin State'],
                                      lexem['End State'],
                                      lexem['Begin Position'],
                                      lexem['End Position'],
                                      lexem['Length']) + '\n'
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
        NotEndOfScript = self.__NotEndOfScript
        ParseNothing = self.__ParseNothing
        ParseDilimiter = self.__ParseDilimiter
        ParseLexem = self.__ParseLexem
        ParseNewLineCharacter = self.__ParseNewLineCharacter
        IncPosition = self.__IncPosition
        GetLexemsAsTextTable = self.__GetLexemsAsTextTable
        DefineNothing = self.__DefineNothing
        DefineDelimiter = self.__DefineDelimiter

        while NotEndOfScript():

            inState = self.__currentState
            inPosition = self.__currentPosition

            if self.__currentState == self.__STATES['STATE_NOTHING']:
                ParseNothing()
                if self.__currentNothing:
                    self.__lexemList.append({'Lexem': self.__currentNothing,
                                             'Lexem Class': 'SPACE',
                                             'Description': DefineNothing(),
                                             'Begin State': inState,
                                             'End State': self.__currentState,
                                             'Begin Position': inPosition,
                                             'End Position': self.__currentPosition,
                                             'Length': len(self.__currentNothing)})
            elif self.__currentState == self.__STATES['STATE_BEGIN_DELIMITER']:
                ParseDilimiter()
                if self.__currentDelimiter:
                    self.__lexemList.append({'Lexem': self.__currentDelimiter,
                                             'Lexem Class': 'DELIMITER',
                                             'Description': DefineDelimiter(),
                                             'Begin State': inState,
                                             'End State': self.__currentState,
                                             'Begin Position': inPosition,
                                             'End Position': self.__currentPosition,
                                             'Length': len(self.__currentDelimiter)})
            elif self.__currentState == self.__STATES['STATE_BEGIN_LEXEM']:
                ParseLexem()
                self.__lexemList.append({'Lexem': self.__currentLexem,
                                         'Lexem Class': 'LEXEM',
                                         'Description': 'LEXEM',
                                         'Begin State': inState,
                                         'End State': self.__currentState,
                                         'Begin Position': inPosition,
                                         'End Position': self.__currentPosition,
                                         'Length': len(self.__currentLexem)})
            
            elif self.__currentState == self.__STATES['STATE_BEGIN_NEWLINE_CHARACTER']:
                ParseNewLineCharacter()
                if self.__currentNothing:
                    self.__lexemList.append({'Lexem': self.__currentNothing,
                                             'Lexem Class': 'NEWLINE',
                                             'Description': DefineNothing(),
                                             'Begin State': inState,
                                             'End State': self.__currentState,
                                             'Begin Position': inPosition,
                                             'End Position': self.__currentPosition,
                                             'Length': len(self.__currentNothing)})
            
            else:
                IncPosition()
        
        #print(GetLexemsAsTextTable())

    #  .▄▄ ·  ▄▄▄·▄▄▌  ▪  ▄▄▄▄▄    .▄▄ · ▄▄▄▄▄ ▄▄▄· ▄▄▄▄▄▄▄▄ .• ▌ ▄ ·. ▄▄▄ . ▐ ▄ ▄▄▄▄▄.▄▄ · 
    #  ▐█ ▀. ▐█ ▄███•  ██ •██      ▐█ ▀. •██  ▐█ ▀█ •██  ▀▄.▀··██ ▐███▪▀▄.▀·•█▌▐█•██  ▐█ ▀. 
    #  ▄▀▀▀█▄ ██▀·██▪  ▐█· ▐█.▪    ▄▀▀▀█▄ ▐█.▪▄█▀▀█  ▐█.▪▐▀▀▪▄▐█ ▌▐▌▐█·▐▀▀▪▄▐█▐▐▌ ▐█.▪▄▀▀▀█▄
    #  ▐█▄▪▐█▐█▪·•▐█▌▐▌▐█▌ ▐█▌·    ▐█▄▪▐█ ▐█▌·▐█ ▪▐▌ ▐█▌·▐█▄▄▌██ ██▌▐█▌▐█▄▄▌██▐█▌ ▐█▌·▐█▄▪▐█
    #   ▀▀▀▀ .▀   .▀▀▀ ▀▀▀ ▀▀▀      ▀▀▀▀  ▀▀▀  ▀  ▀  ▀▀▀  ▀▀▀ ▀▀  █▪▀▀▀ ▀▀▀ ▀▀ █▪ ▀▀▀  ▀▀▀▀ 
    # shitcode
    def __NotEndOfLexems(self):
        return self.__currentPosition < len(self.__lexemList)

    def __GetNextLexem(self):
        self.__currentLexem = []
        if not self.__splitStatementError['ErrorCode'] == 0:
            return False

        if self.__NotEndOfLexems():
            self.__currentLexem = self.__lexemList[self.__currentPosition]
            self.__IncPosition()
            return True
        else:
            return False

    def __GetLastLexem(self):
        self.__DecPosition()
        self.__currentLexem = self.__lexemList[self.__currentPosition-1]

    def __OffsetPosition(self,offset=0):
        self.__currentPosition = self.__currentPosition + offset
        self.__currentLexem = self.__lexemList[self.__currentPosition - 1]

    def __SetError(self,errCode,errText):
        self.__splitStatementError['ErrorCode'] = errCode
        self.__splitStatementError['ErrorText'] = errText

    def __AppendCurrentLexem(self,lexem=None,lexemType=None,lexemLength=None):
        Lexem = self.__GetStatementLexemRow()
        
        Lexem['Lexem']  = lexem       if lexem       else self.__currentLexem['Lexem']
        Lexem['Length'] = lexemLength if lexemLength else self.__currentLexem['Length']
        Lexem['Type']   = lexemType   if lexemType   else 'LEXEM'

        self.__currentStatement.append(Lexem)

    # "--"─────>"\n"
    def __GetOneLineCommentStatement(self):
        oneLineComment = ''

        while self.__GetNextLexem():
            oneLineComment += self.__currentLexem['Lexem']
            
            if self.__IsNewLineLexem():
                break

        self.__AppendCurrentLexem(lexem=oneLineComment,
                                  lexemType='COMMENT',
                                  lexemLength=len(oneLineComment))

    # "/*"──┐    
    #       └──>"*/"
    def __GetMultyLineCommentStatement(self):
        multyLineComment = ''
        closeCommentLexem = ''

        while self.__GetNextLexem():

            if self.__currentLexem['Lexem'] == self.__simpleSymbols['MULTIPLICATION OPERATOR']:
                closeCommentLexem = self.__currentLexem['Lexem']

                if self.__GetNextLexem():
                    closeCommentLexem += self.__currentLexem['Lexem']
                else:
                    self.__SetError(1,'unexpected end of block')
                    return

                if closeCommentLexem == self.__compoundSymbols['MULTI-LINE COMMENT DELIMITER (END)']:
                    break
                else:
                    self.__GetLastLexem()

            multyLineComment += self.__currentLexem['Lexem']

        self.__AppendCurrentLexem(lexem=multyLineComment + closeCommentLexem,
                                  lexemType='MULTYLINE COMMENT',
                                  lexemLength=len(multyLineComment + closeCommentLexem))

    # "'"──┐
    #      └──["''"]──┐
    #                 └──>"'"  
    def __GetStringLexem(self):
        string = ''
        
        if not self.__GetNextLexem():
            self.__SetError(3,'unexpected end of block')
            return

        if not self.__IsApostropheLexem():
            self.__SetError(3,'not string lexem')
            return

        string += self.__currentLexem['Lexem']            
        
        while self.__GetNextLexem():
            if self.__IsApostropheLexem():
                string += self.__currentLexem['Lexem']

                if not self.__GetNextLexem():
                    self.__SetError(3,'unexpected end of block')
                    return
                
                if not self.__IsApostropheLexem():
                    self.__GetLastLexem()
                    break

            string += self.__currentLexem['Lexem']
        
        self.__AppendCurrentLexem(lexem=string,
                                  lexemType='STRING',
                                  lexemLength=len(string))
        

    # '"'─────>'"' 
    def __GetQuotedIdentifierLexem(self):
        quotedIdentifier = ''

        if not self.__GetNextLexem():
            self.__SetError(4,'unexpected end of block')
            return

        if not self.__IsQuoteLexem():
            self.__SetError(4,'not quoted identifier lexem')
            return

        quotedIdentifier += self.__currentLexem['Lexem']
        
        while self.__GetNextLexem():
            quotedIdentifier += self.__currentLexem['Lexem']

            if self.__IsQuoteLexem():
                break

        self.__AppendCurrentLexem(lexem=quotedIdentifier,
                                  lexemType='QUOTED IDENTIFIER',
                                  lexemLength=len(quotedIdentifier))

    # "--"    
    def __IsOneLineComment(self):
        openCommentLexem = self.__currentLexem['Lexem']

        if self.__GetNextLexem():
            openCommentLexem += self.__currentLexem['Lexem']
        else:
            self.__SetError(1,'unexpected end of block')
            return

        self.__GetLastLexem()

        if openCommentLexem == self.__compoundSymbols['SINGLE-LINE COMMENT INDICATOR']:
            return True

        return False

    # "/*"
    def __IsMultyLineComment(self):
        openCommentLexem = self.__currentLexem['Lexem']

        if self.__GetNextLexem():
            openCommentLexem += self.__currentLexem['Lexem']
        else:
            self.__SetError(1,'unexpected end of block')
            return

        self.__GetLastLexem()

        if openCommentLexem == self.__compoundSymbols['MULTI-LINE COMMENT DELIMITER (BEGIN)']:
            return True

        return False

    # "END"<──┐            
    #         └──";"<──┐    
    #                  └──"/"
    def __IsEndOfPlSqlBlock(self):
        if not self.__IsDivisionLexem():
            self.__SetError(2,'not division operator')
            return False
        
        deepBackPosition = 0
        # Ищем ";"
        while True:
            self.__GetLastLexem()
            deepBackPosition += 1
            if not self.__IsIgnoreLexem():
                if not self.__IsStatementTerminatorLexem():
                    self.__OffsetPosition(deepBackPosition)
                    return False
                else:
                    break

        # Ищем "end"
        while True:
            self.__GetLastLexem()
            deepBackPosition += 1
            if not self.__IsIgnoreLexem():
                if not self.__currentLexem['Lexem'].upper() == 'END':
                    self.__OffsetPosition(deepBackPosition)
                    return False
                else:
                    self.__OffsetPosition(deepBackPosition)
                    return True                    
        
        return False

    def __IsSpaceLexem(self):
        return self.__currentLexem['Description'].upper() == 'SPACE'    

    def __IsNewLineLexem(self):
        return self.__currentLexem['Description'].upper() == 'NEWLINE CHARACTER'

    def __IsIgnoreLexem(self):
        return self.__currentLexem['Description'].upper() in ['SPACE','NEWLINE CHARACTER']

    def __IsSubtractionLexem(self):
        return self.__currentLexem['Description'].upper() == 'SUBTRACTION/NEGATION OPERATOR'
    
    def __IsDivisionLexem(self):
        return self.__currentLexem['Description'].upper() == 'DIVISION OPERATOR'
    
    def __IsApostropheLexem(self):
        return self.__currentLexem['Description'].upper() == 'CHARACTER STRING DELIMITER'
    
    def __IsQuoteLexem(self):
        return self.__currentLexem['Description'].upper() == 'QUOTED IDENTIFIER DELIMITER'
    
    def __IsStatementTerminatorLexem(self):
        return self.__currentLexem['Description'].upper() == 'STATEMENT TERMINATOR'

    def __IsCreateLexem(self):
        return self.__currentLexem['Lexem'].upper() == 'CREATE'

    def __IsDeclareLexem(self):
        return self.__currentLexem['Lexem'].upper() == 'DECLARE'

    def __IsENDLexem(self):
        return self.__currentLexem['Lexem'].upper() == 'END'
    
    def __GetPlSqlBlock(self):
        self.__currentStatement = []

        while self.__GetNextLexem():
            # SPACE
            if self.__IsSpaceLexem():
                self.__AppendCurrentLexem(lexem=' ',lexemType='SPACE',lexemLength=1)
            
            # SUBTRACTION/NEGATION OPERATOR
            #  ├ ONELINE COMMENT
            #  └ SUBTRACTION/NEGATION OPERATOR
            elif self.__IsSubtractionLexem():                
                if self.__IsOneLineComment():
                    self.__GetLastLexem()
                    self.__GetOneLineCommentStatement()
                else:
                    self.__AppendCurrentLexem(lexemType='SUBTRACTION/NEGATION OPERATOR')
            
            # DIVISION OPERATOR
            #  ├ END OF PLSQL STATEMENT
            #  ├ MULTYLINE COMMENT
            #  └ DIVISION OPERATOR
            elif self.__IsDivisionLexem():
                if self.__IsEndOfPlSqlBlock():
                    self.__AppendCurrentLexem(lexemType='END PLSQL STATEMENT')
                    break
                elif self.__IsMultyLineComment():
                    self.__GetLastLexem()
                    self.__GetMultyLineCommentStatement()
                else:                
                    self.__AppendCurrentLexem(lexemType='DIVISION OPERATOR')

            # CHARACTER STRING DELIMITER
            #  └ STRING
            #     └ SYMBOL "'"
            elif self.__IsApostropheLexem():
                self.__GetLastLexem()
                self.__GetStringLexem()
            
            # QUOTED IDENTIFIER DELIMITER
            #  └ QUOTED IDENTIFIER
            elif self.__IsQuoteLexem():
                self.__GetLastLexem()
                self.__GetQuotedIdentifierLexem()

            # Lexem "as is"
            else:
                self.__AppendCurrentLexem()
            
        self.__SqlStatements.append(self.__currentStatement)

    def __GetSqlBlock(self):
        self.__currentStatement = []

        while self.__GetNextLexem():
            # SPACE
            if self.__IsSpaceLexem():
                self.__AppendCurrentLexem(lexem=' ',lexemType='SPACE',lexemLength=1)
            
            # SUBTRACTION/NEGATION OPERATOR
            #  ├ ONELINE COMMENT
            #  └ SUBTRACTION/NEGATION OPERATOR
            elif self.__IsSubtractionLexem():
                if self.__IsOneLineComment():
                    self.__GetLastLexem()
                    self.__GetOneLineCommentStatement()
                else:
                    self.__AppendCurrentLexem(lexemType='SUBTRACTION/NEGATION OPERATOR')
                                
            # DIVISION OPERATOR
            #  ├ MULTYLINE COMMENT
            #  └ DIVISION OPERATOR
            elif self.__IsDivisionLexem():
                if self.__IsMultyLineComment():
                    self.__GetLastLexem()
                    self.__GetMultyLineCommentStatement()
                else:                
                    self.__AppendCurrentLexem(lexemType='DIVISION OPERATOR')
            
            # CHARACTER STRING DELIMITER
            #  └ STRING
            #     └ SYMBOL "'"
            elif self.__IsApostropheLexem():
                self.__GetLastLexem()
                self.__GetStringLexem()
            
            # QUOTED IDENTIFIER DELIMITER
            #  └ QUOTED IDENTIFIER
            elif self.__IsQuoteLexem():
                self.__GetLastLexem()
                self.__GetQuotedIdentifierLexem()

            # STATEMENT TERMINATOR
            #  └ END OF SQL STATEMENT
            elif self.__IsStatementTerminatorLexem():
                self.__AppendCurrentLexem(lexemType='END SQL STATEMENT')
                break

            # Lexem "as is"
            else:
                self.__AppendCurrentLexem(lexemType='LEXEM')
            
        self.__SqlStatements.append(self.__currentStatement)

    '''
    PL/SQL::
    CREATE OR REPLACE LIBRARY
    CREATE OR REPLACE FUNCTION
    CREATE OR REPLACE PACKAGE
    CREATE OR REPLACE PACKAGE BODY
    CREATE OR REPLACE PROCEDURE
    CREATE OR REPLACE TRIGGER
    CREATE OR REPLACE TYPE
    CREATE OR REPLACE TYPE BODY
    '''
    def __GetCreateStatement(self):
        self.__IncPosition()
    
    # Out block comment
    def __GetOutBlockComment(self):
        openCommentLexem = ''
        commentBody = ''
        closeCommentLexem = ''
        oneLineComment = False

        self.__currentStatement = []
        self.__statementNumber += 1
        
        if self.__GetNextLexem():
            openCommentLexem += self.__currentLexem['Lexem']
        else:
            self.__SetError(1,'unexpected end of block')
            return

        if self.__GetNextLexem():
            openCommentLexem += self.__currentLexem['Lexem']
        else:
            self.__SetError(1,'unexpected end of block')
            return

        if openCommentLexem not in [self.__compoundSymbols['SINGLE-LINE COMMENT INDICATOR'],
                                    self.__compoundSymbols['MULTI-LINE COMMENT DELIMITER (BEGIN)']]:
            self.__SetError(1,'not comment symbol')
            return
        else:
            if openCommentLexem == self.__compoundSymbols['SINGLE-LINE COMMENT INDICATOR']:
                oneLineComment = True

        while self.__GetNextLexem():
            if oneLineComment and self.__IsNewLineLexem(): 
                closeCommentLexem = self.__currentLexem['Lexem']
                break

            if not oneLineComment and self.__currentLexem['Lexem'] == self.__simpleSymbols['MULTIPLICATION OPERATOR']:
                closeCommentLexem = self.__currentLexem['Lexem']
                
                if self.__GetNextLexem():
                    closeCommentLexem += self.__currentLexem['Lexem']
                else:
                    self.__SetError(1,'unexpected end of block')
                    return
                
                if closeCommentLexem == self.__compoundSymbols['MULTI-LINE COMMENT DELIMITER (END)']:
                    break
                else:
                    self.__DecPosition()

            commentBody += self.__currentLexem['Lexem']
        
        self.__AppendCurrentLexem(lexem=openCommentLexem + commentBody + closeCommentLexem,
                                  lexemType='COMMENT',
                                  lexemLength=len(openCommentLexem + commentBody + closeCommentLexem))
        
        self.__SqlStatements.append(self.__currentStatement)

    def __SplitStatements(self):
        self.__currentLexem = []
        self.__currentPosition = 0
        self.__splitStatementError['ErrorCode'] = 0
        self.__splitStatementError['ErrorText'] = ''

        while self.__GetNextLexem():
            if self.__IsCreateLexem():
                self.__DecPosition()
                self.__GetCreateStatement()
            elif self.__IsDeclareLexem():
                self.__DecPosition()
                self.__GetPlSqlBlock()
            elif self.__IsNewLineLexem():
                pass
            elif self.__IsSpaceLexem():
                pass
            elif self.__IsDivisionLexem() or self.__IsSubtractionLexem():
                self.__DecPosition()
                self.__GetOutBlockComment()
            else:
                self.__DecPosition()
                self.__GetSqlBlock()

    def __GetStatements(self):
        for index, statement in enumerate(self.__SqlStatements):
            statementText = ''
            
            for statementRow in statement:
                if statementRow['Type'] not in ['END PLSQL STATEMENT','END SQL STATEMENT']:
                    statementText += statementRow['Lexem']
            
            self.__SqlTextStatements.append(statementText)

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

        self.__GetStatements()
        
        print(self.__GetLexemsAsTextTable())
        
        if not self.__splitStatementError['ErrorCode'] == 0:
            print('SPLITSTATEMENTERROR::'+self.__splitStatementError['ErrorText'])

        for statement in self.__SqlTextStatements:
            print(statement)

        for index, statement in enumerate(self.__SqlStatements):
            for statementRow in statement:
                print(statementRow)

ScriptParser().LoadScript('''
                          -- some text
                          /* multyline 
                          comment */ 
                          declare
                            a number; -- comment
                            b varchar2(4000) := 'string''_value';
                            c varchar2(4000) := 'string_value2';
                            "hernya" number;
                          begin
                            /** comment2 
                                second row
                            */
                            /*  comment3 */BEGIN NULL; END;
                             
                             IF a<>0 THEN
                                NULL;
                             END IF;   
                            
                            a := a/1;

                            null;
                          end;
                          /
                          -- some text
                          /* multyline 
                          comment */
                          select '1;2' as "ONE", acc.* from daccount_dbt acc;
                          ''')
