(() => {
  'use strict';
  const encoder = new TextEncoder();
  const categoryInfo = {
    annual: { label: 'Annual', korean: '연간', sheet: 'Annual' },
    half_year: { label: 'Half-year', korean: '반기', sheet: 'Half-year' },
    quarterly: { label: 'Quarterly', korean: '분기', sheet: 'Quarterly' }
  };
  const columns = [
    ['period','기간','text'],['year','연도','integer'],['report_code','보고서 코드','text'],
    ['revenue','매출액','integer'],['cost_of_sales','매출원가','integer'],['gross_profit','매출총이익','integer'],
    ['operating_income','영업이익','integer'],['profit_before_tax','법인세차감전이익','integer'],['net_income','당기순이익','integer'],
    ['total_assets','자산총계','integer'],['current_assets','유동자산','integer'],['cash','현금및현금성자산','integer'],
    ['receivables','매출채권','integer'],['inventory','재고자산','integer'],['total_liabilities','부채총계','integer'],
    ['current_liabilities','유동부채','integer'],['total_equity','자본총계','integer'],['operating_cash_flow','영업현금흐름','integer'],
    ['capex','CAPEX','integer'],['free_cash_flow','잉여현금흐름','integer'],['revenue_growth_pct','매출성장률(%)','decimal'],
    ['gross_margin_pct','매출총이익률(%)','decimal'],['operating_margin_pct','영업이익률(%)','decimal'],['net_margin_pct','순이익률(%)','decimal'],
    ['roa_pct','ROA(%)','decimal'],['roe_pct','ROE(%)','decimal'],['current_ratio_pct','유동비율(%)','decimal'],
    ['quick_ratio_pct','당좌비율(%)','decimal'],['debt_to_equity_pct','부채비율(%)','decimal'],['inventory_turnover','재고회전율(회)','decimal'],
    ['dso','DSO(일)','decimal'],['cfo_conversion_pct','CFO 전환율(%)','decimal']
  ];
  let records = [], statusTimer;

  const escapeXml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[char]));
  const columnName = index => { let name=''; for(let n=index+1;n;n=Math.floor((n-1)/26)) name=String.fromCharCode(65+(n-1)%26)+name; return name; };
  const textCell = (ref,value,style=0) => `<c r="${ref}" t="inlineStr" s="${style}"><is><t>${escapeXml(value)}</t></is></c>`;
  const valueCell = (ref,value,type) => {
    if(value===null||value===undefined||value==='') return `<c r="${ref}"/>`;
    if(type==='text'||!Number.isFinite(Number(value))) return textCell(ref,value);
    const style=type==='integer'?2:type==='decimal'?3:0;
    return `<c r="${ref}" s="${style}"><v>${Number(value)}</v></c>`;
  };

  function worksheetXml(rows){
    const header=columns.map(([,label],index)=>textCell(`${columnName(index)}1`,label,1)).join('');
    const body=rows.map((row,rowIndex)=>`<row r="${rowIndex+2}">${columns.map(([key,,type],columnIndex)=>valueCell(`${columnName(columnIndex)}${rowIndex+2}`,row[key],type)).join('')}</row>`).join('');
    const lastColumn=columnName(columns.length-1);
    const widths=columns.map(([,label],index)=>`<col min="${index+1}" max="${index+1}" width="${Math.min(Math.max(label.length*2+4,index===0?15:12),24)}" customWidth="1"/>`).join('');
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:${lastColumn}${rows.length+1}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>${widths}</cols><sheetData><row r="1" ht="24" customHeight="1">${header}</row>${body}</sheetData><autoFilter ref="A1:${lastColumn}${rows.length+1}"/><pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.2" footer="0.2"/></worksheet>`;
  }

  function workbookFiles(rows,info){
    const now=new Date().toISOString();
    return {
      '[Content_Types].xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>`,
      '_rels/.rels':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>`,
      'docProps/app.xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Taihan OpenDART Dashboard</Application></Properties>`,
      'docProps/core.xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>대한전선 ${info.label} 재무데이터</dc:title><dc:creator>Taihan OpenDART Agent</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${now}</dcterms:modified></cp:coreProperties>`,
      'xl/workbook.xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="${info.sheet}" sheetId="1" r:id="rId1"/></sheets></workbook>`,
      'xl/_rels/workbook.xml.rels':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
      'xl/styles.xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0"/><numFmt numFmtId="165" formatCode="0.00"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Arial"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1455A2"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFDCE5F0"/></left><right style="thin"><color rgb="FFDCE5F0"/></right><top style="thin"><color rgb="FFDCE5F0"/></top><bottom style="thin"><color rgb="FFDCE5F0"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`,
      'xl/worksheets/sheet1.xml':worksheetXml(rows)
    };
  }

  const crcTable=(()=>{const table=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;table[n]=c>>>0}return table})();
  function crc32(bytes){let crc=0xffffffff;for(const byte of bytes)crc=crcTable[(crc^byte)&0xff]^(crc>>>8);return(crc^0xffffffff)>>>0}
  function dosDateTime(date){const year=Math.max(date.getFullYear(),1980);return{time:(date.getHours()<<11)|(date.getMinutes()<<5)|Math.floor(date.getSeconds()/2),date:((year-1980)<<9)|((date.getMonth()+1)<<5)|date.getDate()}}
  function concat(parts){const size=parts.reduce((sum,part)=>sum+part.length,0),output=new Uint8Array(size);let offset=0;for(const part of parts){output.set(part,offset);offset+=part.length}return output}
  function header(size){return new DataView(new ArrayBuffer(size))}
  function zip(files){
    const localParts=[],centralParts=[],stamp=dosDateTime(new Date());let offset=0;
    Object.entries(files).forEach(([filename,content])=>{
      const name=encoder.encode(filename),body=encoder.encode(content),checksum=crc32(body),local=header(30);
      local.setUint32(0,0x04034b50,true);local.setUint16(4,20,true);local.setUint16(6,0x0800,true);local.setUint16(8,0,true);local.setUint16(10,stamp.time,true);local.setUint16(12,stamp.date,true);local.setUint32(14,checksum,true);local.setUint32(18,body.length,true);local.setUint32(22,body.length,true);local.setUint16(26,name.length,true);local.setUint16(28,0,true);localParts.push(new Uint8Array(local.buffer),name,body);
      const central=header(46);central.setUint32(0,0x02014b50,true);central.setUint16(4,20,true);central.setUint16(6,20,true);central.setUint16(8,0x0800,true);central.setUint16(10,0,true);central.setUint16(12,stamp.time,true);central.setUint16(14,stamp.date,true);central.setUint32(16,checksum,true);central.setUint32(20,body.length,true);central.setUint32(24,body.length,true);central.setUint16(28,name.length,true);central.setUint16(30,0,true);central.setUint16(32,0,true);central.setUint16(34,0,true);central.setUint16(36,0,true);central.setUint32(38,0,true);central.setUint32(42,offset,true);centralParts.push(new Uint8Array(central.buffer),name);offset+=30+name.length+body.length;
    });
    const centralDirectory=concat(centralParts),end=header(22),count=Object.keys(files).length;end.setUint32(0,0x06054b50,true);end.setUint16(4,0,true);end.setUint16(6,0,true);end.setUint16(8,count,true);end.setUint16(10,count,true);end.setUint32(12,centralDirectory.length,true);end.setUint32(16,offset,true);end.setUint16(20,0,true);return concat([...localParts,centralDirectory,new Uint8Array(end.buffer)]);
  }

  function showStatus(message){const element=document.getElementById('export-status');clearTimeout(statusTimer);element.textContent=message;element.hidden=false;statusTimer=setTimeout(()=>{element.hidden=true},3200)}
  function closeMenu(){const menu=document.getElementById('excel-menu'),toggle=document.getElementById('excel-toggle');menu.hidden=true;toggle.setAttribute('aria-expanded','false')}
  function download(category){
    const info=categoryInfo[category],rows=records.filter(row=>row.category===category).slice().sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    if(!info||!rows.length){showStatus('선택한 기간의 데이터가 없습니다.');return}
    const blob=new Blob([zip(workbookFiles(rows,info))],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}),url=URL.createObjectURL(blob),anchor=document.createElement('a');
    anchor.href=url;anchor.download=`대한전선_${info.label}_재무데이터.xlsx`;document.body.appendChild(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);showStatus(`${info.korean} 데이터 ${rows.length}건을 Excel로 저장했습니다.`);
  }

  document.getElementById('pdf-download').addEventListener('click',()=>window.print());
  document.getElementById('excel-toggle').addEventListener('click',event=>{event.stopPropagation();const menu=document.getElementById('excel-menu'),open=menu.hidden;menu.hidden=!open;event.currentTarget.setAttribute('aria-expanded',String(open));if(open)menu.querySelector('button').focus()});
  document.getElementById('excel-menu').addEventListener('click',event=>{const button=event.target.closest('[data-export-category]');if(!button)return;download(button.dataset.exportCategory);closeMenu()});
  document.addEventListener('click',event=>{if(!event.target.closest('.excel-control'))closeMenu()});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu()});
  window.DashboardExport={setData(value){records=Array.isArray(value)?value:[]}};
})();
