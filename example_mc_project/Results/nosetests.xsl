<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0" >
<xsl:template match="/">
 
          <html>

               <head>
               <script xmlns="http://www.w3.org/1999/xhtml" type="text/javascript">
         <![CDATA[
         function filter2 (phrase, _id){
	var words = phrase.value.toLowerCase().split(" ");
	var table = document.getElementById(_id);
	var ele;
	for (var r = 1; r < table.rows.length; r++){
		ele = table.rows[r].innerHTML.replace(/<[^>]+>/g,"");
	        var displayStyle = 'none';
	        for (var i = 0; i < words.length; i++) {
		    if (ele.toLowerCase().indexOf(words[i])>=0)
			displayStyle = '';
		    else {
			displayStyle = 'none';
			break;
		    }
	        }
		table.rows[r].style.display = displayStyle;
	}
}
]]>
</script>
                    <link rel="stylesheet" type="text/css" href="nosetests.css"/>
               </head>
               <body>
                <h2>AMARA WEBRIVER TESTS</h2>
                
               <h3 class="summary">total tests: <xsl:value-of select="testsuite/@tests"/>
               <xsl:variable name="errs" select="testsuite/@errors"/>
               <xsl:variable name="fails" select="testsuite/@failures"/>
               
                | failures: <xsl:value-of select="$errs+$fails" />
                | skip: <xsl:value-of select="testsuite/@skip" />
                </h3>
                <div class='filter'>
                <form name="input" type="select">
                 <select onChange="filter2(this, 'results', this.options[this.selectedIndex].value)">
                    <option value=" ">Show All Results</option>
                    <option value="pass">Pass</option>
                    <option value="fail">Fail</option>
                    <option value="skip">Skip</option>
                 </select> 
                </form> 
                </div>
                
                <table id='results'>
                  <tr>
                    <th>Screenshot</th>
                    <th>Test Case</th>
                  </tr>                
 
                  <xsl:for-each select="testsuite/testcase">
                    <xsl:variable name="class">
                       <xsl:value-of select="@classname"/>
                    </xsl:variable>                 
                    <xsl:variable name="test">
                       <xsl:value-of select="@name"/>
                    </xsl:variable>    
                    <xsl:variable name="status">
                        <xsl:choose>
                        <xsl:when test="./failure">fail</xsl:when>
                        <xsl:when test="./skipped">skip</xsl:when>
                        <xsl:when test="./error">fail</xsl:when>
                        <xsl:otherwise>pass</xsl:otherwise>
                        </xsl:choose>                      
                    </xsl:variable>
                    
                    <xsl:variable name="message">
                     <xsl:choose>
                      <xsl:when test="./failure"><xsl:value-of select="./failure"/></xsl:when>
                        <xsl:when test="./error"><xsl:value-of select="./error"/></xsl:when>
                         <xsl:when test="./skipped"><xsl:value-of select="./skipped"/></xsl:when>
                          <xsl:otherwise></xsl:otherwise>
                     </xsl:choose>
                    </xsl:variable>
                    
                   <xsl:call-template name='testdata'>
                     <xsl:with-param name="test" select="$test"/>
                     <xsl:with-param name="status" select="$status"/>
                     <xsl:with-param name="message" select="$message"/>
                     <xsl:with-param name="class" select="$class"/>
                   </xsl:call-template>    
                  </xsl:for-each>
                 </table>
                 <div id="table-bottom"><p> <br/> </p></div>
                </body>

              </html>
    </xsl:template>
    
    <xsl:template name='testdata'>
     <xsl:param name="test"/>
     <xsl:param name="status"/>
     <xsl:param name="message"/>
     <xsl:param name="class"/>
  
    <tr><xsl:attribute name="id"><xsl:value-of select="$status"/></xsl:attribute>
          
     <xsl:variable name="screenshot_name">
         <xsl:value-of select="$class"/>.<xsl:value-of select="$test"/>.png</xsl:variable>
      
     <td id="screenshot">
     <xsl:choose>
        <xsl:when test="$status='skip'"><p><xsl:value-of select="$status"/></p></xsl:when>
        <xsl:otherwise>
             <a>
                <xsl:attribute name="href"><xsl:value-of select="$screenshot_name"/></xsl:attribute>
             <span><xsl:value-of select="$status"/></span>
             <img id="hover-only">
                <xsl:attribute name="src"><xsl:value-of select="$screenshot_name"/></xsl:attribute>
             </img>
            </a>
        </xsl:otherwise>
      </xsl:choose>
          </td>
          
     <td>
      <xsl:choose>
       <xsl:when test="$status='pass'">
           <span class="status"><div id="pass_message"><xsl:value-of select="$class"/>.<xsl:value-of select="$test"/></div>
           </span>
      </xsl:when>
      <xsl:otherwise>
         <span class="status"><div id="err_message">
           <a href="#"><xsl:value-of select="$class"/>.<xsl:value-of select="$test"/>
              <span>Test Name:  <xsl:value-of select="$test"/>
              <br/>filename.Classname:  <xsl:value-of select="$class"/><p><xsl:value-of select="$message"/>
              </p></span>
           </a></div>
         </span>
      </xsl:otherwise>
     </xsl:choose>
     </td>
    </tr>
    </xsl:template>

    
</xsl:stylesheet>


