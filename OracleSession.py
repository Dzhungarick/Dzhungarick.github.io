# coding: utf8

import os
import sys
import sublime
import sublime_plugin
import binascii

if sublime.arch() == 'x32':
    sys.path.append(os.path.join(os.path.dirname(__file__), "lib","cx_Oracle_32"))
elif sublime.arch() == 'x64':
    sys.path.append(os.path.join(os.path.dirname(__file__), "lib","cx_Oracle_64"))

import cx_Oracle

#        ▄▄▄   ▄▄▄·  ▄▄· ▄▄▌  ▄▄▄ .    .▄▄ · ▄▄▄ ..▄▄ · .▄▄ · ▪         ▐ ▄      ▄▄· ▄▄▌   ▄▄▄· .▄▄ · .▄▄ · 
#  ▪     ▀▄ █·▐█ ▀█ ▐█ ▌▪██•  ▀▄.▀·    ▐█ ▀. ▀▄.▀·▐█ ▀. ▐█ ▀. ██ ▪     •█▌▐█    ▐█ ▌▪██•  ▐█ ▀█ ▐█ ▀. ▐█ ▀. 
#   ▄█▀▄ ▐▀▀▄ ▄█▀▀█ ██ ▄▄██▪  ▐▀▀▪▄    ▄▀▀▀█▄▐▀▀▪▄▄▀▀▀█▄▄▀▀▀█▄▐█· ▄█▀▄ ▐█▐▐▌    ██ ▄▄██▪  ▄█▀▀█ ▄▀▀▀█▄▄▀▀▀█▄
#  ▐█▌.▐▌▐█•█▌▐█ ▪▐▌▐███▌▐█▌▐▌▐█▄▄▌    ▐█▄▪▐█▐█▄▄▌▐█▄▪▐█▐█▄▪▐█▐█▌▐█▌.▐▌██▐█▌    ▐███▌▐█▌▐▌▐█ ▪▐▌▐█▄▪▐█▐█▄▪▐█
#   ▀█▄▀▪.▀  ▀ ▀  ▀ ·▀▀▀ .▀▀▀  ▀▀▀      ▀▀▀▀  ▀▀▀  ▀▀▀▀  ▀▀▀▀ ▀▀▀ ▀█▄▀▪▀▀ █▪    ·▀▀▀ .▀▀▀  ▀  ▀  ▀▀▀▀  ▀▀▀▀
class OracleSession:
    def __init__(self):
        self.settings = sublime.load_settings('OracleDevTools.sublime-settings')        
        self.maxRows         = self.settings.get('rownum')
        self.user            = self.settings.get('username')
        self.password        = self.settings.get('password')
        self.connString      = self.settings.get('host') + ':' + str(self.settings.get('port')) + '/' + self.settings.get('dbname')
        self.connAs          = self.settings.get('connect_as')
        self.createNewWindow = self.settings.get('new_window')
        self.showErrorWindow = self.settings.get('error_window')
        self.dbms_output     = self.settings.get('dbms_output')
        self.autocommit      = self.settings.get('autocommit')

        self.currentConnection = None
        self.currentConnection = None
        self.encoding          = None
        self.oracleSessionError= ''

        self.output = ''

        __connectAS = { 'NORMAL' : 0,
                        'SYSDBA' : cx_Oracle.SYSDBA,
                        'SYSOPER': cx_Oracle.SYSOPER }
        try:
            connMode = __connectAS[self.connAs.upper()]
        except KeyError, e:
            connMode = __connectAS['NORMAL']
            print('unknown mode "{0}"::set "normal"'.format(self.connAs))

        os.environ['NLS_LANG'] = self.settings.get('nls_lang')
        
        try:
            self.currentConnection = cx_Oracle.connect(self.user, 
                                                       self.password, 
                                                       self.connString,
                                                       mode = connMode)
            
            self.currentConnection.cursor().callproc("DBMS_APPLICATION_INFO.SET_ACTION", ["sublime session"])
            
            self.encoding = self.currentConnection.encoding
            
            self.currentConnection.autocommit = self.autocommit
            
            if self.dbms_output:
                self.currentConnection.cursor().callproc("dbms_output.enable")
            
            print('successfull connected::{0} ({1})'.format(self.user,self.connString))
        except cx_Oracle.DatabaseError, e:
            print('OracleSession :: ' + str(e))
            self.oracleSessionError = str(e)
    
    def ClearOutput(self):
        self.output = ''

    def PutOutputText(self,text):
        self.output += text

    def OutputIsEmpty(self):
        return True if len(self.output) == 0 else False

    def IsLobValue(self,value):
        return type(value) is cx_Oracle.LOB

    def IsConnected(self):
        try:
            self.currentConnection.ping()
        except:
            if not self.oracleSessionError: 
                self.oracleSessionError = 'not connected'
            return False
        else:
            return True

    def ShowCurrentConnection(self):
        self.ShowError('{0} ({1})'.format(self.user,self.connString))

    def Reconnect(self):
        # ???
        print('\n')
        if self.IsConnected():
            try:
                self.currentConnection.close()
                print('connection::{0} ({1})::closed'.format(self.user,self.connString))
            except cx_Oracle.Error, e:
                self.ShowError(str(e))

        print('reconnecting...')
        self.__init__()

        if not self.IsConnected():
            self.ShowError()
        else:
            print('OK')

    def Disconnect(self):
        print('\n')
        print('current connection::{0} ({1})'.format(self.user,self.connString))
        print('disconnecting...')
        try:
            self.currentConnection.close()
        except AttributeError, e:
            print('not connected')
        except cx_Oracle.Error, e:
            self.oracleSessionError(str(e))
        print('OK')

    def GetDbmsOutput(self):
        statusVar = self.currentConnection.cursor().var(cx_Oracle.NUMBER)
        lineVar   = self.currentConnection.cursor().var(cx_Oracle.STRING)
        output    = ''

        while True:
            self.currentConnection.cursor().callproc("dbms_output.get_line", (lineVar, statusVar))
            if statusVar.getvalue() != 0:
                break
            output += lineVar.getvalue() + "\n"
        return output

    def cursor(self):
        return self.currentConnection.cursor() if self.currentConnection else None

    def execute(self,sqlText,**kwargs):
        try:
            result = self.cursor().execute(sqlText, kwargs)
        except cx_Oracle.Error, e:
            self.oracleSessionError = str(e)
            return None

        return result

    def ShowError(self,errText=None):
        if errText == None:
            errText = self.sessionError

        if self.showErrorWindow:
            sublime.message_dialog(errText.decode('UTF-8'))
        print(errText)
    
    def ClearSessionError(self):
        self.oracleSessionError = ''
    
    def HasError(self):
        return not len(self.oracleSessionError) == 0

    @property
    def sessionError(self):
        error = self.oracleSessionError
        self.ClearSessionError()
        return error

    def OutputResult(self,sublimeView,sublimeEdit,windowName='result'):
        if self.createNewWindow:
            outWindow = sublimeView.window().new_file()
            outWindow.insert(sublimeEdit,0,self.output)
            outWindow.set_name(windowName)
        else:
            print(self.output)

        self.ClearOutput()

    def GetObjectDDL(self,objectName,objectType,objectOwner=None):
        sqlText = " SELECT DBMS_METADATA.GET_DDL(:object_type, UPPER(:object_name), :object_owner) FROM DUAL "
        result = self.execute(sqlText,object_type  = objectType,
                                      object_name  = objectName,
                                      object_owner = objectOwner).fetchone()
        return result[0].read().decode(self.encoding) + '\n\n' if result else ''

    def GetObjectSource(self,objectName,objectType,objectOwner=None):
        sqlText = ''' SELECT TEXT
                        FROM ALL_SOURCE
                       WHERE     LOWER(NAME) = LOWER(:object_name) 
                             AND TYPE = :object_type
                             AND OWNER = NVL(:object_owner,USER)
                     ORDER BY LINE
                  '''

        output = ''
        object_body = ''
        object_body_max_len = 0
        result = self.execute(sqlText, object_name  = objectName, 
                                       object_type  = objectType,
                                       object_owner = objectOwner)
        for object_body_line in result.fetchall():
            object_body = object_body + object_body_line[0]

            if len(object_body_line[0]) > object_body_max_len:
                object_body_max_len = len(object_body_line[0])

        output +=    '-'*object_body_max_len                     + '\n' \
                   + object_body.decode(currentSession.encoding) + '\n' \
                   + '-'*object_body_max_len                     + '\n'
        return output

    def GetObjectErrors(self,objectName,objectType,objectOwner=None):
        sqlText = ''' SELECT *
                        FROM ALL_ERRORS
                       WHERE      LOWER(NAME) = LOWER(:object_name)
                              AND LOWER(TYPE) = LOWER(:object_type)
                              AND OWNER       = NVL(:object_owner,USER)
                     ORDER BY LINE
                  '''
        errors = ''
        result = self.execute(sqlText, object_name  = objectName, 
                                       object_type  = objectType,
                                       object_owner = objectOwner)
        
        for object_error in result.fetchall():
            error_descr = 'TYPE'     + ' :: ' +     object_error[7]  + ' ' + \
                          'LINE'     + ' :: ' + str(object_error[4]) + ' ' + \
                          'POSITION' + ' :: ' + str(object_error[5])
            
            errors = errors + error_descr          +   '\n' \
                            + '-'*len(error_descr) +   '\n' \
                            + object_error[6]      + '\n\n'

        if not errors:
            errors = 'No errors                    \n'
            errors = errors + '-'*len(errors) + '\n\n'

        return errors

    def GetObjectDescr(self,objectName,objectType,objectOwner=None):
        sqlText = ''' SELECT *
                        FROM ALL_OBJECTS
                       WHERE     LOWER(OBJECT_NAME) = LOWER(:object_name)
                             AND LOWER(OBJECT_TYPE) = LOWER(:object_type)
                             AND OWNER = NVL(:object_owner,USER)
                     ORDER BY OBJECT_TYPE
                  '''
        result = self.execute(sqlText, object_name  = objectName,
                                       object_type  = objectType,
                                       object_owner = objectOwner)
        
        return self.GetSqlResultAsText(result)  

    def GetObjectType(self,objectName):
        sqlText = ''' SELECT OBJECT_TYPE 
                        FROM USER_OBJECTS
                       WHERE LOWER(OBJECT_NAME) = LOWER(:object_name) 
                  '''             
        result = self.execute(sqlText, object_name = objectName).fetchone()
        
        return result[0] if result else None

    # у объекта могут быть синонимы
    def GetObjectName(self,objectName):
        sqlText = ''' SELECT TABLE_NAME
                        FROM ALL_SYNONYMS
                       WHERE     LOWER(SYNONYM_NAME) = LOWER(:object_name)
                             AND TABLE_OWNER IN (USER,'SYS')
                  '''            
        result = self.execute(sqlText, object_name = objectName).fetchone()
        return result[0] if result else objectName

    def GetObjectArguments(self,objectName,objectType,objectOwner=None):
        output = ''
        if objectType == 'PACKAGE':
            sqlText = ''' SELECT PROCEDURE_NAME,
                                 SUBPROGRAM_ID
                            FROM ALL_PROCEDURES
                           WHERE     lower(OBJECT_NAME) = lower(:object_name)
                                 AND OWNER = NVL(:object_owner,USER)
                                 AND PROCEDURE_NAME IS NOT NULL
                         ORDER BY SUBPROGRAM_ID        
                      '''
            result = self.execute(sqlText, object_name  = objectName,
                                           object_owner = objectOwner)
            for procedure in result.fetchall():
                output += procedure[0] + ' :: \n' 
                sqlText = ''' SELECT ARGUMENT_NAME "Argument",
                                     POSITION      "Position",
                                     DATA_TYPE     "Type",
                                     DEFAULTED     "Defaulted",
                                     IN_OUT        "In/Out",
                                     PLS_TYPE      "PLS Type"
                                FROM ALL_ARGUMENTS
                               WHERE     lower(PACKAGE_NAME) = lower(:object_name)
                                     AND OWNER = NVL(:object_owner,USER)
                                     AND OBJECT_NAME = :procedure_name
                                     AND SUBPROGRAM_ID = :subprogram_id
                             ORDER BY POSITION        
                          '''               
                resultArg = self.execute(sqlText, object_name    = objectName,
                                                  object_owner   = objectOwner,
                                                  procedure_name = procedure[0],
                                                  subprogram_id  = procedure[1])
                output += self.GetSqlResultAsText(resultArg)

        return output

    def GetSqlResultAsText(self,cursor):
        if cursor:
            tableStringA = []

            result = cursor.fetchall() if not self.maxRows else cursor.fetchmany(self.maxRows)

            for row in result:
                rowStringA = []

                for index, value in enumerate(row):
                    if type(value) is str:
                        if value == chr(0) or value == chr(1):
                            rowStringA.append('NullString')
                        elif not value:
                            rowStringA.append('EmptyString')
                        elif cursor.description[index][1] is cx_Oracle.BINARY:
                            rowStringA.append(binascii.b2a_hex(value))
                        else:
                            rowStringA.append(value.decode(self.encoding))
                    elif value is None: 
                        rowStringA.append('NullValue')
                    elif type(value) is cx_Oracle.LOB:
                        rowStringA.append('LOB')
                    else:
                        rowStringA.append(str(value))

                tableStringA.append(rowStringA)

            columnNamesA = []
            for description in cursor.description:
                columnNamesA.append(description[0])

            # Определяем ширину каждого столбца
            lenValueA = [0]*len(columnNamesA)
            for row in tableStringA:
                for index, value in enumerate(row):
                    lenValueA[index] = len(value) if lenValueA[index] < len(value) else lenValueA[index]

            for index, columnName in enumerate(columnNamesA):
                lenValueA[index] = len(columnName) if len(columnName) > lenValueA[index] else lenValueA[index]

            # Формируем формат строки
            rowFormat = '|'
            for lenVal in lenValueA:
                rowFormat += ' %-' + str(lenVal) + 's |'

            rowLen = len(rowFormat%tuple(columnNamesA))

            outText = '|' + '='*(rowLen-2) + '|'    + '\n' + \
                      rowFormat%tuple(columnNamesA) + '\n' + \
                      '|' + '-'*(rowLen-2) + '|'    + '\n'
                    
            for row in tableStringA:
                outText += rowFormat%tuple(row) + '\n'
                    
            outText += '|' + '='*(rowLen-2) + '|' + '\n\n'

            return outText
        else:
            return ''