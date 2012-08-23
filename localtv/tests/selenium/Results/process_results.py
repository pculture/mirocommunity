from lxml import etree
import os

class ProcessResults():
    def transform_to_html(self, results_xml, xsl, output_html):
        f = open(xsl)
        o = open(output_html, 'w')
        resultdoc = etree.parse(results_xml)        
        rroot = resultdoc.getroot()
         

        xslt_root = etree.XML(f.read())
        transform = etree.XSLT(xslt_root)
        result_tree = transform(resultdoc)
        o.write(str(result_tree))

if __name__ == "__main__":
    ProcessResults().transform_to_html(results_xml = os.path.join(os.path.dirname(__file__), 'nosetests.xml'),
                                       xsl = os.path.join(os.path.dirname(__file__), 'nosetests.xsl'),
                                       output_html = os.path.join(os.path.dirname(__file__), 'results.html'))

