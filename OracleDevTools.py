# coding: utf8

'''
      ▄▄▄   ▄▄▄·  ▄▄· ▄▄▌  ▄▄▄ .    ·▄▄▄▄  ▄▄▄ . ▌ ▐·    ▄▄▄▄▄            ▄▄▌  .▄▄ · 
▪     ▀▄ █·▐█ ▀█ ▐█ ▌▪██•  ▀▄.▀·    ██▪ ██ ▀▄.▀·▪█·█▌    •██  ▪     ▪     ██•  ▐█ ▀. 
 ▄█▀▄ ▐▀▀▄ ▄█▀▀█ ██ ▄▄██▪  ▐▀▀▪▄    ▐█· ▐█▌▐▀▀▪▄▐█▐█•     ▐█.▪ ▄█▀▄  ▄█▀▄ ██▪  ▄▀▀▀█▄
▐█▌.▐▌▐█•█▌▐█ ▪▐▌▐███▌▐█▌▐▌▐█▄▄▌    ██. ██ ▐█▄▄▌ ███      ▐█▌·▐█▌.▐▌▐█▌.▐▌▐█▌▐▌▐█▄▪▐█
 ▀█▄▀▪.▀  ▀ ▀  ▀ ·▀▀▀ .▀▀▀  ▀▀▀     ▀▀▀▀▀•  ▀▀▀ . ▀       ▀▀▀  ▀█▄▀▪ ▀█▄▀▪.▀▀▀  ▀▀▀▀ 

'''

import sys
import os
#sys.path.append(os.path.dirname(sys.executable))
sys.path.append(os.path.join(os.path.dirname(__file__), "lib","cx_Oracle"))
#sys.path.append(os.path.join(os.path.dirname(__file__)))
#sys.path.append(os.path.join(os.path.dirname(__file__), "lib","printtable"))
import sublime
import sublime_plugin
import cx_Oracle
import binascii
import time
from SqlScriptParser import ScriptParser

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
        
    def IsConnected(self):
        try:
            self.currentConnection.ping()
        except:
            self.oracleSessionError = 'not connected'
            return False
        else:
            return True

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
            self.ShowError(self.oracleSessionError)
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
        return  self.cursor().execute(sqlText, kwargs)

    def ShowError(self,errText):
        if self.showErrorWindow:
            sublime.message_dialog(errText.decode('UTF-8'))
        print(errText)
    
    def OutputResult(self,sublimeView,sublimeEdit,outputText,windowName='result'):
        if self.createNewWindow:
            outWindow = sublimeView.window().new_file()
            outWindow.insert(sublimeEdit,0,outputText)
            outWindow.set_name(windowName)
        else:
            print(outputText)

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
        #ALL_ARGUMENTS
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
                pass
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

currentSession = OracleSession()

#  ▄▄▄ .▐▄• ▄ ▄▄▄ . ▄▄·     .▄▄ · .▄▄▄  ▄▄▌  
#  ▀▄.▀· █▌█▌▪▀▄.▀·▐█ ▌▪    ▐█ ▀. ▐▀•▀█ ██•  
#  ▐▀▀▪▄ ·██· ▐▀▀▪▄██ ▄▄    ▄▀▀▀█▄█▌·.█▌██▪  
#  ▐█▄▄▌▪▐█·█▌▐█▄▄▌▐███▌    ▐█▄▪▐█▐█▪▄█·▐█▌▐▌
#   ▀▀▀ •▀▀ ▀▀ ▀▀▀ ·▀▀▀      ▀▀▀▀ ·▀▀█. .▀▀▀
# Выполнить запрос
# "command": "exec_sql"
class ExecSqlCommand(sublime_plugin.TextCommand):  
    def run(self, edit): 
        view = self.view
        
        region = view.sel()[0]
        if not region.empty():
            selection = view.substr(region)
        else:
            currentSession.ShowError('Необходимо выделить запрос')
            return

        if not currentSession.IsConnected():
            currentSession.ShowError(currentSession.oracleSessionError)
            return              

        try:
            result = currentSession.execute(selection)
        except cx_Oracle.Error, e:
            currentSession.ShowError(str(e))
            return 

        if result:
            begin_time = time.time()
            output = currentSession.GetSqlResultAsText(result)
            print(time.time() - begin_time)
        else:
            output = "PL/SQL procedure successfully completed. \n\n"
            if currentSession.dbms_output:
                output += "DBMS OUTPUT :: \n\n"
                output += currentSession.GetDbmsOutput()

        if output:
            currentSession.OutputResult(view,edit,output,'SQL result')

#  ▄▄▄ .▐▄• ▄ ▄▄▄ . ▄▄·     .▄▄ · .▄▄▄  ▄▄▌      .▄▄ ·  ▄▄· ▄▄▄  ▪   ▄▄▄·▄▄▄▄▄
#  ▀▄.▀· █▌█▌▪▀▄.▀·▐█ ▌▪    ▐█ ▀. ▐▀•▀█ ██•      ▐█ ▀. ▐█ ▌▪▀▄ █·██ ▐█ ▄█•██  
#  ▐▀▀▪▄ ·██· ▐▀▀▪▄██ ▄▄    ▄▀▀▀█▄█▌·.█▌██▪      ▄▀▀▀█▄██ ▄▄▐▀▀▄ ▐█· ██▀· ▐█.▪
#  ▐█▄▄▌▪▐█·█▌▐█▄▄▌▐███▌    ▐█▄▪▐█▐█▪▄█·▐█▌▐▌    ▐█▄▪▐█▐███▌▐█•█▌▐█▌▐█▪·• ▐█▌·
#   ▀▀▀ •▀▀ ▀▀ ▀▀▀ ·▀▀▀      ▀▀▀▀ ·▀▀█. .▀▀▀      ▀▀▀▀ ·▀▀▀ .▀  ▀▀▀▀.▀    ▀▀▀
# Выполнить скрипт
# "command": "exec_sql_script"
class ExecSqlScriptCommand(sublime_plugin.TextCommand):  
    def run(self, edit):
        region = self.view.sel()[0]
        
        if not region.empty():
            scriptText = self.view.substr(region)
        else:
            scriptText = self.view.substr(sublime.Region(0, self.view.size()))
        
        parser = ScriptParser().LoadScript(scriptText)

        if not currentSession.IsConnected():
            currentSession.ShowError(currentSession.oracleSessionError)
            return

        cursor = currentSession.cursor()

        output = ''

        for index, statement in enumerate(parser.SqlStatements):
            try:
                result = cursor.execute(statement)
            except cx_Oracle.Error, e:
                output += 'STATEMENT::#' + str(index) + '\n'
                output += 'STATEMENT TEXT::' + '\n'
                output += statement + '\n'
                output += 'ERRORTEXT::' + str(e) + '\n'
            else:
                if result:
                    output += 'STATEMENT::#' + str(index) + '\n'
                    output += currentSession.GetSqlResultAsText(result)
                else:
                    output += 'STATEMENT::#' + str(index) + '\n'
                    output += 'completed' + '\n\n'
                    if currentSession.dbms_output:
                        dbms_output = currentSession.GetDbmsOutput()
                        if dbms_output:
                            output += "DBMS OUTPUT :: \n" + dbms_output + '\n'
            
        currentSession.OutputResult(self.view,edit,output,'script result')                

#  .▄▄ · ▄▄▄ .▄▄▄▄▄▄▄▄▄▄▪   ▐ ▄  ▄▄ • .▄▄ · 
#  ▐█ ▀. ▀▄.▀·•██  •██  ██ •█▌▐█▐█ ▀ ▪▐█ ▀. 
#  ▄▀▀▀█▄▐▀▀▪▄ ▐█.▪ ▐█.▪▐█·▐█▐▐▌▄█ ▀█▄▄▀▀▀█▄
#  ▐█▄▪▐█▐█▄▄▌ ▐█▌· ▐█▌·▐█▌██▐█▌▐█▄▪▐█▐█▄▪▐█
#   ▀▀▀▀  ▀▀▀  ▀▀▀  ▀▀▀ ▀▀▀▀▀ █▪·▀▀▀▀  ▀▀▀▀ 
# Открыть настройки 
# "command": "oracle_dev_tools_settings"
class OracleDevToolsSettingsCommand(sublime_plugin.TextCommand):  
    def run(self, edit):
        self.menu = ['Find object',
                     'Describe',
                    #'Get script for object',
                     'Explain Plan',
                     'Extract CLOB from SELECT',
                     'Reconnect',
                     'Disconnect',
                     'Open settings']
        self.edit = edit
        self.view.window().show_quick_panel(self.menu,self.on_menu_done)

    def on_menu_done(self, index):
        menu = self.menu
        view = self.view

        if index == -1:
            return

        selection = None
        region = view.sel()[0]

        if not region.empty():
            selection = view.substr(region)

        if menu[index] == 'Open settings':
            self.view.window().open_file(os.path.join(sublime.packages_path(), "OracleDevTools", "OracleDevTools.sublime-settings"))
        elif menu[index] == 'Find object':
            if not currentSession.IsConnected():
                currentSession.ShowError(currentSession.oracleSessionError)
                return
            if not selection:
                currentSession.ShowError('Необходимо выделить текст')
                return

            sqlText = '''SELECT OBJECT_NAME, OBJECT_TYPE
                          FROM ALL_OBJECTS
                         WHERE     LOWER (OBJECT_NAME) LIKE LOWER ('%' || :obj_name || '%')
                               AND OWNER IN (USER, 'SYS')
                       GROUP BY OBJECT_NAME, OBJECT_TYPE
                       ORDER BY OBJECT_TYPE, OBJECT_NAME
                      '''
            result = currentSession.execute(sqlText, obj_name = selection)                         
            foundedObjects = [] 

            for row in result.fetchall():
                foundedObjects.append(list(row))

            self.foundedObjects = foundedObjects
            self.view.window().show_quick_panel(foundedObjects, self.on_find_object_done)   
            return
        elif menu[index] == 'Reconnect':
            currentSession.Reconnect()
        elif menu[index] == 'Disconnect':
            currentSession.Disconnect()
        elif menu[index] == 'Describe':
            if not currentSession.IsConnected():
                currentSession.ShowError(currentSession.oracleSessionError)
                return
            if not selection:
                currentSession.ShowError('Необходимо выделить текст')
                return
            output = ''
            selection = currentSession.GetObjectName(selection)

            sqlText = ''' SELECT OBJECT_TYPE, OWNER
                            FROM ALL_OBJECTS
                           WHERE LOWER (OBJECT_NAME) = LOWER (:obj_name) AND OWNER IN (USER, 'SYS')             
                      '''
            result = currentSession.execute(sqlText, obj_name = selection)                        
            
            object_type = result.fetchone()
            if not object_type:
                currentSession.ShowError('Объект не найден')
                return

            output  = 'OBJECT NAME :: ' + selection.upper() + '\n'
            output += 'OBJECT TYPE :: ' + object_type[0]    + '\n\n'

            if object_type[0] == 'TABLE':
                output = output + 'COLUMNS :: \n'
                
                sqlText = ''' SELECT COLUMN_NAME "Column Name",
                                     COLUMN_ID   "ID",
                                     DATA_TYPE   "Data Type",
                                     NULLABLE    "Nullable"
                                FROM ALL_TAB_COLUMNS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:tablename)
                                     AND OWNER = :tableowner
                             ORDER BY COLUMN_ID
                          '''
                result = currentSession.execute(sqlText,tablename  = selection, 
                                                        tableowner = object_type[1])
                output += currentSession.GetSqlResultAsText(result)

                output += 'INDEXES :: \n'
                
                sqlText = ''' SELECT IND_COLUMNS.INDEX_NAME      "Index Name",
                                     INDEXES.UNIQUENESS          "Uniqueness",
                                     INDEXES.DEGREE              "Degree",
                                     IND_COLUMNS.COLUMN_NAME     "Column Name",
                                     IND_COLUMNS.DESCEND         "Order",
                                     IND_COLUMNS.COLUMN_POSITION "Position"
                                FROM ALL_IND_COLUMNS IND_COLUMNS, ALL_INDEXES INDEXES
                               WHERE     IND_COLUMNS.INDEX_NAME = INDEXES.INDEX_NAME
                                     AND LOWER(INDEXES.TABLE_NAME) = LOWER(:tablename)
                                     AND IND_COLUMNS.TABLE_OWNER = INDEXES.TABLE_OWNER
                                     AND INDEXES.TABLE_OWNER = :tableowner
                             ORDER BY IND_COLUMNS.INDEX_NAME, IND_COLUMNS.COLUMN_POSITION
                          ''' 
                result = currentSession.execute(sqlText,tablename  = selection,
                                                        tableowner = object_type[1])
                output += currentSession.GetSqlResultAsText(result)

                output += 'CONSTRAINTS :: \n'
                
                sqlText = ''' SELECT CONSTRAINTS.CONSTRAINT_NAME   "Constraint Name",
                                     CONS_COLUMNS.COLUMN_NAME      "Column Name",
                                     CONSTRAINTS.CONSTRAINT_TYPE   "Constraint Type",
                                     CONSTRAINTS.SEARCH_CONDITION  "Search Condition",
                                     CONSTRAINTS.R_CONSTRAINT_NAME "Ref. Constraint Name",
                                     CONSTRAINTS.STATUS            "Status",
                                     CONSTRAINTS.DELETE_RULE       "Delete Rule",
                                     CONSTRAINTS.DEFERRABLE        "Deferrable",
                                     CONSTRAINTS.DEFERRED          "Deferred",
                                     CONSTRAINTS.VALIDATED         "Validated",
                                     CONSTRAINTS.BAD               "Bad",
                                     CONSTRAINTS.RELY              "Rely"
                                FROM ALL_CONSTRAINTS CONSTRAINTS, ALL_CONS_COLUMNS CONS_COLUMNS
                                WHERE     LOWER(CONSTRAINTS.TABLE_NAME) = LOWER(:tablename)
                                      AND CONSTRAINTS.CONSTRAINT_NAME = CONS_COLUMNS.CONSTRAINT_NAME
                                      AND CONSTRAINTS.OWNER = CONS_COLUMNS.OWNER
                                      AND CONSTRAINTS.OWNER = :tableowner
                              ORDER BY CONS_COLUMNS.POSITION
                          '''
                result = currentSession.execute(sqlText,tablename  = selection,
                                                        tableowner = object_type[1])
                output += currentSession.GetSqlResultAsText(result)

                output += 'TRIGGERS :: \n'
                
                sqlText = ''' SELECT TRIGGER_NAME      "Trigger Name",
                                     TRIGGER_TYPE      "Trigger Type",
                                     STATUS            "Status",
                                     TRIGGERING_EVENT  "Triggering Event",
                                     WHEN_CLAUSE       "When Clause"
                                FROM ALL_TRIGGERS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:tablename)
                                     AND TABLE_OWNER = :tableowner
                          '''   
                result = currentSession.execute(sqlText,tablename  = selection,
                                                        tableowner = object_type[1])
                output += currentSession.GetSqlResultAsText(result)
            
            elif object_type[0] == 'VIEW':
                output += 'COLUMNS :: \n'
                
                sqlText = ''' SELECT COLUMN_NAME "Column Name",
                                     COLUMN_ID   "ID",
                                     DATA_TYPE   "Data Type",
                                     NULLABLE    "Nullable"
                                FROM ALL_TAB_COLUMNS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:view_name)
                                     AND OWNER = :view_owner
                             ORDER BY COLUMN_ID
                          '''
                result = currentSession.execute(sqlText,view_name  = selection, 
                                                        view_owner = object_type[1])
                output += currentSession.GetSqlResultAsText(result)
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, 'VIEW', object_type[1])

            elif object_type[0] == 'TRIGGER':               
                output += 'DESCRIPTION :: \n'
                output += currentSession.GetObjectDescr(selection, 'TRIGGER', object_type[1])

                sqlText = ''' SELECT TRIGGER_NAME,
                                     TRIGGER_TYPE,
                                     TABLE_NAME,
                                     STATUS,
                                     TRIGGERING_EVENT,
                                     WHEN_CLAUSE
                                FROM USER_TRIGGERS
                               WHERE LOWER(TRIGGER_NAME) = LOWER(:triggername)
                          '''
                result = currentSession.execute(sqlText,triggername = selection)
                output += currentSession.GetSqlResultAsText(result)

                output += 'ERRORS :: \n'
                output += currentSession.GetObjectErrors(selection, 'TRIGGER', object_type[1])
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, 'TRIGGER', object_type[1])

            elif object_type[0] == 'PACKAGE' or object_type[0] == 'PACKAGE BODY':                   
                output += 'DESCRIPTION :: \n'
                output += currentSession.GetObjectDescr (selection, 'PACKAGE', object_type[1])
                output += currentSession.GetObjectDescr (selection, 'PACKAGE BODY', object_type[1])
                output += currentSession.GetObjectArguments(selection, 'PACKAGE', object_type[1])
                output += 'ERRORS :: \n'
                output += currentSession.GetObjectErrors(selection, 'PACKAGE', object_type[1])
                output += currentSession.GetObjectErrors(selection, 'PACKAGE BODY', object_type[1])
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, 'PACKAGE', object_type[1])

            elif object_type[0] == 'FUNCTION':
                output += 'DESCRIPTION :: \n'
                output += currentSession.GetObjectDescr (selection, 'FUNCTION', object_type[1])
                output += 'ERRORS :: \n'
                output += currentSession.GetObjectErrors(selection, 'FUNCTION', object_type[1])
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, 'FUNCTION', object_type[1])
            elif object_type[0] == 'PROCEDURE':
                output += 'DESCRIPTION :: \n'
                output += currentSession.GetObjectDescr (selection, 'PROCEDURE', object_type[1])
                output += 'ERRORS :: \n'
                output += currentSession.GetObjectErrors(selection, 'PROCEDURE', object_type[1])
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, 'PROCEDURE', object_type[1])
            elif object_type[0] == 'INDEX':
                output += 'DESCRIPTION :: \n'
                output += currentSession.GetObjectDescr (selection, 'INDEX', object_type[1])
                sqlText = ''' SELECT IND_COLUMNS.COLUMN_NAME     "Column Name",
                                     INDEXES.UNIQUENESS          "Uniqueness",
                                     INDEXES.DEGREE              "Degree",                                           
                                     IND_COLUMNS.DESCEND         "Order",
                                     IND_COLUMNS.COLUMN_POSITION "Position"
                                FROM ALL_IND_COLUMNS IND_COLUMNS, ALL_INDEXES INDEXES
                               WHERE     IND_COLUMNS.INDEX_NAME = INDEXES.INDEX_NAME
                                     AND LOWER(INDEXES.INDEX_NAME) = LOWER(:indexname)
                                     AND IND_COLUMNS.TABLE_OWNER = INDEXES.TABLE_OWNER
                                     AND INDEXES.TABLE_OWNER = :indexowner
                             ORDER BY IND_COLUMNS.INDEX_NAME, IND_COLUMNS.COLUMN_POSITION
                          ''' 
                result = currentSession.execute(sqlText,indexname  = selection,
                                                        indexowner = object_type[1])
                output += currentSession.GetSqlResultAsText(result)
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, 'INDEX', object_type[1])
            else:
                output += 'DESCRIPTION :: \n'
                output += currentSession.GetObjectDescr (selection, object_type[0], object_type[1])
                output += 'DDL :: \n'
                output += currentSession.GetObjectDDL(selection, object_type[0], object_type[1])

            if output:
                currentSession.OutputResult(view,self.edit,output,selection)

        elif menu[index] == 'Extract CLOB from SELECT':
            if not currentSession.IsConnected():
                currentSession.ShowError(currentSession.oracleSessionError)
                return
            if not selection:
                currentSession.ShowError('Необходимо выделить текст')
                return
            try:
                result = currentSession.execute(selection)
            except cx_Oracle.Error, e:
                currentSession.ShowError(str(e))
            else:
                output = ''
                
                if result:
                    # Почему-то если извлекать больше 50 строк, то возникает ошибка:
                    # cx_Oracle.ProgrammingError: LOB variable no longer valid after subsequent fetch
                    for index_j, row in enumerate(result.fetchmany(currentSession.maxRows if currentSession.maxRows <= 50 else 50)):
                        for index_i, value in enumerate(row):
                            if type(value) is cx_Oracle.LOB:
                                output += result.description[index_i][0] + ' :: ROWNUM :: ' + str(index_j) + '\n'
                                output += '-'*len(result.description[index_i][0])               + '\n'
                                output += value.read().decode(currentSession.encoding)          + '\n'
                                output += '-'*len(value.read().decode(currentSession.encoding)) + '\n\n'
                if output:
                    currentSession.OutputResult(view,self.edit,output,'Extract LOB')
                else:
                    currentSession.ShowError('No Clob')
        
        # TODO: dbms_metadata.get_ddl
        elif menu[index] == 'Get script for object':
            if not currentSession.IsConnected():
                currentSession.ShowError(currentSession.oracleSessionError)
                return
            object_type = currentSession.GetObjectType(selection)
            print(object_type)
            pass

        elif menu[index] == 'Explain Plan':
            if not currentSession.IsConnected():
                currentSession.ShowError(currentSession.oracleSessionError)
                return
            if not selection:
                currentSession.ShowError('Необходимо выделить запрос')
                return
            
            sqlText = 'EXPLAIN PLAN FOR ' + selection
            try:
                result = currentSession.execute(sqlText)
            except cx_Oracle.Error, e:
                currentSession.ShowError(str(e))                
                return
            
            sqlText = 'SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY(FORMAT=>\'ALL\'))'
            try:
                result = currentSession.execute(sqlText)
            except cx_Oracle.Error, e:
                currentSession.ShowError(str(e))                
                return

            output  = 'STATEMENT ::  \n'
            output += selection + '\n\n'                    
            output += 'PLAN ::       \n'
            for row in result.fetchall():
                output += row[0] + '\n'

            currentSession.OutputResult(view,self.edit,output,'EXPLAIN PLAN')                    

    def on_find_object_done(self, index):
        if index == -1:
            return
        else:
            self.view.replace(self.edit, self.view.sel()[0], self.foundedObjects[index][0])