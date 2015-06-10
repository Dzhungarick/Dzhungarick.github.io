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
    class Connection:
        def __init__(self,connSettings={}):
            self.user = connSettings.get('username','no user')
            self.password = connSettings.get('password','no passwod')
            self.host = connSettings.get('host','no host')
            self.port = connSettings.get('port',0)
            self.dbname = connSettings.get('dbname','no dbname')
            self.connAs = connSettings.get('connect_as','no mode')
        
        @property
        def connectionString(self):
            return '{0}:{1}/{2}'.format(self.host,self.port,self.dbname)

        @property
        def connectionMessage(self):
            return '{0} ({1})'.format(self.user,self.connectionString)

        @property
        def connectionMode(self):
            __connectAS = { 'NORMAL' : 0,
                            'SYSDBA' : cx_Oracle.SYSDBA,
                            'SYSOPER': cx_Oracle.SYSOPER }
            try:
                connMode = __connectAS[self.connAs.upper()]
            except KeyError, e:
                connMode = __connectAS['NORMAL']
                print('unknown mode "{0}"::set "normal"'.format(self.connAs))
            
            return connMode

    def __init__(self,reconnect=False,connectionName=None):
        self.settings = sublime.load_settings('OracleDevTools.sublime-settings')        
        # Максимальное количество строк в выборке
        self.maxRows         = self.settings.get('rownum',50)
        # Создавать новое окно для вывода информации. Если False, то вывод происходит в консоль
        self.createNewWindow = self.settings.get('new_window',False)
        # Показывать окно с ошибкой 
        self.showErrorWindow = self.settings.get('error_window',True)
        # Включить dbms_output
        self.dbms_output     = self.settings.get('dbms_output',False)
        # Автоматическая фиксация транзакции
        self.autocommit      = self.settings.get('autocommit',True)
        #  Автоматически подключаться
        self.autoconnect     = self.settings.get('autoconnect',False)

        # Если имя определено, то это новое подключение
        if connectionName:
            self.autoconnect = True            
        
        # Если имя не определено, и это не реконнект, то пытаемся получить имя по умолчанию
        if not connectionName and not reconnect:
            connectionName = self.settings.get('default_connection',None)

        # Если не удалось получить имя, то не подключаемся
        if not connectionName:
            self.autoconnect = False

        # При реконнекте не обновляем настройки подключения
        if not reconnect:
            self.connectionParams = self.Connection(self.settings.get('connections',{}).get(connectionName,{}))

        self.currentConnection = None
        self.encoding          = None
        self.oracleSessionError= ''

        self.output = ''

        os.environ['NLS_LANG'] = self.settings.get('nls_lang','.')

        if self.autoconnect or reconnect:
            try:
                self.currentConnection = cx_Oracle.connect(self.connectionParams.user, 
                                                           self.connectionParams.password, 
                                                           self.connectionParams.connectionString,
                                                           mode = self.connectionParams.connectionMode)
                
                self.currentConnection.cursor().callproc("DBMS_APPLICATION_INFO.SET_ACTION", ["sublime session"])

                self.encoding = self.currentConnection.encoding
                self.currentConnection.autocommit = self.autocommit
                
                if self.dbms_output:
                    self.currentConnection.cursor().callproc("dbms_output.enable")
                
                print('successfull connected::{0}'.format(self.connectionParams.connectionMessage))
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
        if self.connectionParams:
            self.ShowError(self.connectionParams.connectionMessage)
        else:
            self.ShowError('not connected')

    def GetConnectionsList(self):
        connectionsList = []
        for connectionName in self.settings.get('connections',{}):
            connectionsList.append([connectionName,
                                    self.Connection(self.settings.get('connections')[connectionName]).connectionMessage])
        if len(connectionsList) == 0:
            connectionsList.append(['no connections','no connections'])

        return connectionsList
        
    def Reconnect(self,connectionName=None):
        # ???
        print('\n')
        if self.IsConnected():
            try:
                self.currentConnection.close()
                print('connection::{0}::closed'.format(self.connectionParams.connectionMessage))
            except cx_Oracle.Error, e:
                self.ShowError(str(e))

        print('reconnecting...')
        self.__init__(False if connectionName else True,connectionName)
        if not self.IsConnected():
            self.ShowError()
        else:
            print('OK')

    def Disconnect(self):
        print('\n')
        if not self.connectionParams:
            print('not connected')
            return

        print('current connection::{0})'.format(self.connectionParams.connectionMessage))
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

    def ShowError(self,errText=None,dbencode=False):
        if errText == None:
            errText = self.sessionError
        
        if dbencode:
            encoding = self.encoding
        else:
            encoding = 'UTF-8'

        if self.showErrorWindow:
            try:
                sublime.message_dialog(errText.decode(encoding))
            except:
                errText = '{0!r}'.format(errText)
                sublime.message_dialog(errText)
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

    def OutputResult(self,windowName='result'):
        if self.createNewWindow:
            outWindow = sublime.active_window().new_file()
            outWindow.set_name(windowName)
            
            edit = outWindow.begin_edit()
            outWindow.insert(edit,0,self.output)
            edit = outWindow.end_edit(edit)
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
                   + object_body.decode(self.encoding) + '\n' \
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

        return errors.decode(self.encoding)

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
        def processRow(row):
            def getEmptyRow(length):
                return ['']*length

            rows = [getEmptyRow(len(row))]
            
            rowFirst = 0
            columnTypeIndex = 1
            
            for columnIndex, value in enumerate(row):
                # Строка
                if type(value) is str:
                    # Пустые строки
                    if value == chr(0) or value == chr(1):
                        rows[rowFirst][columnIndex] = 'NullString'
                    # NULL
                    elif not value:
                        rows[rowFirst][columnIndex] = 'EmptyString'
                    # тип RAW
                    elif cursor.description[columnIndex][columnTypeIndex] is cx_Oracle.BINARY:
                        rows[rowFirst][columnIndex] = binascii.b2a_hex(value)
                    else:
                        strings = value.split('\n')
                        # Обработка многострочного текста
                        for rowIndex, string in enumerate(strings):
                            # Добавляем строки
                            while len(rows) <= rowIndex:
                                rows.append(getEmptyRow(len(row)))
                            rows[rowIndex][columnIndex] = string.decode(self.encoding)
                # NULL
                elif value is None: 
                    rows[rowFirst][columnIndex] = 'NullValue'
                # Большие объекты здесь не разворачиваем
                elif type(value) is cx_Oracle.LOB:
                    rows[rowFirst][columnIndex] = 'LOB'
                # Остальные типы, которые легко приводятся к строке
                else:
                    rows[rowFirst][columnIndex] = str(value)

            return rows
        # end processRow
        
        if cursor:
            tableStringA = []

            try:
                result = cursor.fetchall() if not self.maxRows else cursor.fetchmany(self.maxRows)
            except cx_Oracle.DatabaseError, e:
                self.oracleSessionError = str(e).decode(self.encoding)
                return ''

            for indexRow, row in enumerate(result):
                rows = processRow(row)

                for processedRow in rows:
                    tableStringA.append(processedRow)

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