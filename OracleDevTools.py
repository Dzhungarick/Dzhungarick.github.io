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
import sublime
import sublime_plugin
import time
from SqlScriptParser import ScriptParser
from OracleSession import OracleSession

session = OracleSession()

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
            session.ShowError('Необходимо выделить запрос')
            return

        if not session.IsConnected():
            session.ShowError()
            return              
        
        result = session.execute(selection)
        if session.HasError():
            session.ShowError()
            return 

        if result:
            begin_time = time.time()
            session.PutOutputText(session.GetSqlResultAsText(result))
            print(time.time() - begin_time)
        else:
            session.PutOutputText('PL/SQL procedure successfully completed. \n\n')
            if session.dbms_output:
                session.PutOutputText('DBMS OUTPUT :: \n\n')
                session.PutOutputText(session.GetDbmsOutput())

        if not session.OutputIsEmpty():
            session.OutputResult(view,edit,'SQL result')

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
            offset = region.begin()
        else:
            scriptText = self.view.substr(sublime.Region(0, self.view.size()))
            offset = 0
        
        regions = self.view.get_regions("checkStatementMark")            

        self.view.erase_regions("checkStatementMark")

        parser = ScriptParser().LoadScript(scriptText)

        if not session.IsConnected():
            session.ShowError()
            return

        for index, statement in enumerate(parser.SqlStatements):
            result = session.execute(statement['Statement Text'])
            
            self.view.add_regions("statementMark", 
                                  [sublime.Region(statement['Statement Begin Position']+offset, statement['Statement End Position']+offset)], 
                                  "string", 
                                  "bookmark", 
                                  sublime.DRAW_OUTLINED)
            
            firstLine = self.view.lines(self.view.get_regions("statementMark")[0])[0]
            self.view.show(firstLine)

            session.PutOutputText('STATEMENT::#' + str(index) + '\n')
            if session.HasError():
                errText = session.sessionError
                session.PutOutputText('STATEMENT TEXT::' + '\n')
                session.PutOutputText(statement['Statement Text'] + '\n')
                session.PutOutputText('ERRORTEXT::' + errText + '\n')

                if not sublime.ok_cancel_dialog(errText+'\nContinue?'):
                    break
            else:
                if result:
                    session.PutOutputText(session.GetSqlResultAsText(result))
                else:
                    session.PutOutputText('completed' + '\n\n')

                    if session.dbms_output:
                        dbms_output = session.GetDbmsOutput()
                        if dbms_output:
                            session.PutOutputText("DBMS OUTPUT :: \n" + dbms_output + '\n')
        
        self.view.erase_regions("statementMark")
        
        self.view.add_regions("checkStatementMark", 
                              regions, 
                              "string", 
                              "bookmark", 
                              sublime.DRAW_OUTLINED)

        session.OutputResult(self.view,edit,'script result')                

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
                     'Explain Plan',
                     'Extract CLOB from SELECT',
                     'Check Script',
                     'Reconnect',
                     'Disconnect',
                     'Show current connection string',
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
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить текст')
                return

            sqlText = '''SELECT OBJECT_NAME, OBJECT_TYPE
                           FROM ALL_OBJECTS
                          WHERE    LOWER (OBJECT_NAME) LIKE LOWER ('%' || :obj_name || '%')
                               AND OWNER IN (USER, 'SYS')
                       GROUP BY OBJECT_NAME, OBJECT_TYPE
                       ORDER BY OBJECT_TYPE, OBJECT_NAME
                      '''
            result = session.execute(sqlText, obj_name = selection)                         
            foundedObjects = [] 

            for row in result.fetchall():
                foundedObjects.append(list(row))

            self.foundedObjects = foundedObjects
            self.view.window().show_quick_panel(foundedObjects, self.on_find_object_done)   
            return
        
        elif menu[index] == 'Reconnect':
            session.Reconnect()
        
        elif menu[index] == 'Disconnect':
            session.Disconnect()
        
        elif menu[index] == 'Show current connection string':
            session.ShowCurrentConnection()
        
        elif menu[index] == 'Describe':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить текст')
                return
            
            selection = session.GetObjectName(selection)

            sqlText = ''' SELECT OBJECT_TYPE, OWNER
                            FROM ALL_OBJECTS
                           WHERE LOWER (OBJECT_NAME) = LOWER (:obj_name) AND OWNER IN (USER, 'SYS')             
                      '''
            result = session.execute(sqlText, obj_name = selection)                        
            
            object_type = result.fetchone()
            
            if not object_type:
                session.ShowError('Объект не найден')
                return

            session.PutOutputText('OBJECT NAME :: ' + selection.upper() + '\n')
            session.PutOutputText('OBJECT TYPE :: ' + object_type[0]    + '\n\n')

            if object_type[0] == 'TABLE':
                session.PutOutputText('COLUMNS :: \n')

                sqlText = ''' SELECT COLUMN_NAME "Column Name",
                                     COLUMN_ID   "ID",
                                     DATA_TYPE   "Data Type",
                                     NULLABLE    "Nullable"
                                FROM ALL_TAB_COLUMNS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:tablename)
                                     AND OWNER = :tableowner
                             ORDER BY COLUMN_ID
                          '''
                result = session.execute(sqlText,tablename  = selection, 
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))

                session.PutOutputText('INDEXES :: \n')
                
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
                result = session.execute(sqlText,tablename  = selection,
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('CONSTRAINTS :: \n')
                
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
                result = session.execute(sqlText,tablename  = selection,
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('TRIGGERS :: \n')

                sqlText = ''' SELECT TRIGGER_NAME      "Trigger Name",
                                     TRIGGER_TYPE      "Trigger Type",
                                     STATUS            "Status",
                                     TRIGGERING_EVENT  "Triggering Event",
                                     WHEN_CLAUSE       "When Clause"
                                FROM ALL_TRIGGERS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:tablename)
                                     AND TABLE_OWNER = :tableowner
                          '''   
                result = session.execute(sqlText,tablename  = selection,
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
            
            elif object_type[0] == 'VIEW':
                session.PutOutputText('COLUMNS :: \n')
                
                sqlText = ''' SELECT COLUMN_NAME "Column Name",
                                     COLUMN_ID   "ID",
                                     DATA_TYPE   "Data Type",
                                     NULLABLE    "Nullable"
                                FROM ALL_TAB_COLUMNS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:view_name)
                                     AND OWNER = :view_owner
                             ORDER BY COLUMN_ID
                          '''
                result = session.execute(sqlText,view_name  = selection, 
                                                 view_owner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'VIEW', object_type[1]))

            elif object_type[0] == 'TRIGGER':               
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'TRIGGER', object_type[1]))

                sqlText = ''' SELECT TRIGGER_NAME     "Trigger Name",
                                     TRIGGER_TYPE     "Trigger Type",
                                     TABLE_NAME       "Table Name",
                                     STATUS           "Status",
                                     TRIGGERING_EVENT "Triggering Event",
                                     WHEN_CLAUSE      "When Clause"
                                FROM USER_TRIGGERS
                               WHERE LOWER(TRIGGER_NAME) = LOWER(:triggername)
                          '''
                result = session.execute(sqlText,triggername = selection)
                
                session.PutOutputText(session.GetSqlResultAsText(result))

                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'TRIGGER', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'TRIGGER', object_type[1]))

            elif object_type[0] == 'PACKAGE' or object_type[0] == 'PACKAGE BODY':                   
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'PACKAGE', object_type[1]))
                session.PutOutputText(session.GetObjectDescr(selection, 'PACKAGE BODY', object_type[1]))
                session.PutOutputText(session.GetObjectArguments(selection, 'PACKAGE', object_type[1]))
                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'PACKAGE', object_type[1]))
                session.PutOutputText(session.GetObjectErrors(selection, 'PACKAGE BODY', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'PACKAGE', object_type[1]))
                
            elif object_type[0] == 'FUNCTION':
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'FUNCTION', object_type[1]))
                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'FUNCTION', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'FUNCTION', object_type[1]))
                
            elif object_type[0] == 'PROCEDURE':
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'PROCEDURE', object_type[1]))
                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'PROCEDURE', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'PROCEDURE', object_type[1]))

            elif object_type[0] == 'INDEX':
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'INDEX', object_type[1]))

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
                result = session.execute(sqlText,indexname  = selection,
                                                 indexowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'INDEX', object_type[1]))
                
            else:
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, object_type[0], object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, object_type[0], object_type[1]))
            
            if not session.OutputIsEmpty():
                session.OutputResult(view,self.edit,selection)

        elif menu[index] == 'Extract CLOB from SELECT':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить текст')
                return

            result = session.execute(selection)
            if session.HasError():
                session.ShowError()
                return
            else:
                if result:
                    # Почему-то если извлекать больше 50 строк, то возникает ошибка:
                    # cx_Oracle.ProgrammingError: LOB variable no longer valid after subsequent fetch
                    for index_j, row in enumerate(result.fetchmany(session.maxRows if session.maxRows <= 50 else 50)):
                        for index_i, value in enumerate(row):
                            if session.IsLobValue(value):
                                session.PutOutputText(result.description[index_i][0] + ' :: ROWNUM :: ' + str(index_j) + '\n')
                                session.PutOutputText('-'*len(result.description[index_i][0]) + '\n')
                                session.PutOutputText(value.read().decode(session.encoding) + '\n')
                                session.PutOutputText('-'*len(value.read().decode(session.encoding)) + '\n\n')
                
                if not session.OutputIsEmpty():
                    session.OutputResult(view,self.edit,'Extract LOB')
                else:
                    session.ShowError('No Clob')
        
        # TODO: dbms_metadata.get_ddl
        elif menu[index] == 'Get script for object':
            if not session.IsConnected():
                session.ShowError()
                return

            object_type = session.GetObjectType(selection)
            print(object_type)
            pass

        elif menu[index] == 'Explain Plan':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить запрос')
                return
            
            sqlText = 'EXPLAIN PLAN FOR ' + selection

            result = session.execute(sqlText)
            if session.HasError():
                session.ShowError()
                return
            
            sqlText = 'SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY(FORMAT=>\'ALL\'))'

            result = session.execute(sqlText)
            if session.HasError():
                session.ShowError()
                return

            session.PutOutputText('STATEMENT ::  \n')
            session.PutOutputText(selection + '\n\n')
            session.PutOutputText('PLAN ::       \n')
            
            for row in result.fetchall():
                session.PutOutputText(row[0] + '\n')

            session.OutputResult(view,self.edit,'EXPLAIN PLAN')                    

        elif menu[index] == 'Check Script':
            region = view.sel()[0]

            if not region.empty():
                scriptText = view.substr(region)
            else:
                scriptText = view.substr(sublime.Region(0, view.size()))

            outWindow = view.window().new_file()
            outWindow.insert(self.edit,0,scriptText)
            outWindow.set_name('Parsed Script')

            parser = ScriptParser().LoadScript(scriptText)
            regions = []

            for index, statement in enumerate(parser.SqlStatements):
                regions.append(sublime.Region(statement['Statement Begin Position'], statement['Statement End Position']))
            
            outWindow.add_regions("checkStatementMark", 
                                  regions, 
                                  "entity", 
                                  "bookmark", 
                                  sublime.DRAW_OUTLINED)

    def on_find_object_done(self, index):
        if index == -1:
            return
        else:
            self.view.replace(self.edit, self.view.sel()[0], self.foundedObjects[index][0])