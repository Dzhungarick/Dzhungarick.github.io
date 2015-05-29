-- test outblock comments
/* test 
   anonymous block */
declare
    a number; -- test oneline comment
    /* test double apostrophe */
    b varchar2(4000) := 'string''_value';
    c varchar2(4000) := 'string_value2';
    "hernya" number;
begin
    /** 
     * test multyline comment 
     * second row
     */
    
    /*  comment */BEGIN NULL; END;
     
    IF a<>0 THEN
        NULL;
    END IF;   
    
    -- test dbms_output
    dbms_output.put_line('test_text');

    null;
end;
/

declare
    a number := 1;
begin
    /* test ora error */
    a := a/0;
end;
/    

/** 
 * test sql statement 
 */
select '1;2' as "ONE", acc.* from daccount_dbt acc where rownum<10;

/* test create object statement */
create or replace function foo(a number)
return number
is
begin
    return a*1005;
end;
/

select foo(222) from dual;
  
drop function foo;

/* test create table statement */
create table superTable (a number);

drop table superTable;

EXPLAIN PLAN FOR
  SELECT   vl.sid,
           vl.TYPE,
           vl.lmode,
           vl.ctime,
           vl.block,
           vs.username,
           vs.lockwait,
           vs.status,
           vs.schemaname,
           vs.osuser,
           vs.machine,
           vs.terminal,
           vs.program,
           vs.sql_id,
           vs.prev_sql_id,
           VS.MODULE,
           O.OBJECT_NAME
    FROM   v$lock vl,
           v$session vs,
           v$locked_object l,
           dba_objects o
   WHERE       vl.TYPE = 'TX'
           AND vl.sid = vs.sid
           AND vs.username = USER
           AND vl.SID = L.SESSION_ID
           AND l.object_id = o.object_id
ORDER BY   vl.ctime DESC;

SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY(FORMAT=>'ALL'));

select * from v$parameter p where p.name like 'nls%';