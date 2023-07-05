import numpy as np
import pandas as pd
import geopandas as gpd
#import geoviews
import sqlite3 as sql
import cartopy.crs as ccrs
#import hvplot.pandas
import panel as pn
import holoviews as hv
#from holoviews import streams,opts
from bokeh.models import HoverTool
hv.extension('bokeh')
import hvplot
hvplot.extension('bokeh')
import hvplot.pandas
import geoviews as gv
from holoviews import opts

class MeteoPlot:
    def __init__(self,df) -> None:
        self.df=df
        self.variables=list(self.df.variable.unique().astype(str))
        self.tooltips = [('Stazione', '@city'),('Altitudine s.l.m.','@z'),('Data','@{time}{%F}'),('Valore', '@value')]
        self.hover = HoverTool(tooltips=self.tooltips, formatters={'@{time}': 'datetime'})
        self.options=dict(color='value',cmap='plasma',size=10, width=700,height=700,xaxis=None,yaxis=None,colorbar=True,line_color='black',tools=[self.hover,'tap','lasso_select'],responsive=True)

        self.emptyhist = hv.Histogram((np.zeros(10),np.zeros(10)),kdims='value').opts(framewise=True,axiswise=True)
        self.options2=dict(width=1400,height=400, tools=[self.hover],responsive=True)
        emptyserie = pd.DataFrame({'time':df.time.unique(),'value':0,'city':"Seleziona una stazione"})
        self.empty=hv.Curve(emptyserie,kdims='time',vdims=['value','city']).relabel('').opts(**self.options2).relabel("Time series")
        self.options3=dict(width=600,framewise=True,box_fill_color='lightgreen',tools=['hover'],show_grid=True,shared_axes=False)

    def get_dfq(self,index,var,time,agg):
        self.dfq=self.df[(self.df.variable==var) & (self.df.time>time[0]) & (self.df.time<time[1])].groupby(["city","x","y","z"],as_index=False)["value"].agg(agg)#.groupby("city")["value"].transform(agg).eq(self.df["value"])]#
        return gv.Points(self.dfq,kdims=['x','y'],crs=ccrs.epsg(3003)).opts(**self.options)
#pnts=hv.Points(df.loc[df[(df.variable==select_var.value) ].groupby("city")["value"].transform("max").eq(df["value"])],kdims=['x','y']).opts(**options)


    def get_series(self,index,var,time):
        if not index:
            return self.empty
        self.dfs = self.df[(self.df.variable==var) & (self.df["city"]==self.dfq.iloc[index[0]]["city"]) & (self.df.time>time[0]) & (self.df.time<time[1])]
        return hv.Curve(self.dfs,kdims='time',vdims=['value','city']).opts(framewise=True,**self.options2).relabel(self.dfq.iloc[index[0]]["city"])
    
    def get_histo(self,index,var,time,bin):
        if not index:
            return self.emptyhist
        self.dfh = self.df[(self.df.variable==var) & (self.df["city"]==self.dfq.iloc[index[0]]["city"]) & (self.df.time>time[0]) & (self.df.time<time[1])]
        freqs,edges = np.histogram(self.dfh.value,bin)
        return hv.Histogram((edges,freqs),kdims='value').opts(framewise=True,axiswise=True,**self.options2)
    
    def get_summary(self,index,var,time):
        if not index:
            return hv.Table(pd.DataFrame({'index':[],'value':[]}))
        self.dfh = self.df[(self.df.variable==var) & (self.df["city"]==self.dfq.iloc[index[0]]["city"]) & (self.df.time>time[0]) & (self.df.time<time[1])]["value"].describe().reset_index()
        return hv.Table(self.dfh).relabel("Stats")#.opts(**self.options2)
    
    def get_boxwhiskers(self,index,var,time):
        if not index:
            return hv.BoxWhisker(pd.DataFrame({'month':[i for i in range(1,13)],'value':[0]*12}),'month','value').opts(**self.options3).relabel('Distribuzioni mensili')
        self.dfb = self.df[(self.df.variable==var) & (self.df["city"]==self.dfq.iloc[index[0]]["city"]) & (self.df.time>time[0]) & (self.df.time<time[1])]
        self.dfb['month']=self.dfb.time.dt.month
        return hv.BoxWhisker(self.dfb,'month','value').sort().opts(**self.options3).relabel('Distribuzioni mensili')
#stres2=[sel_city,posxy,select_var,time]


def main():
    conn=sql.connect(r'variabili_meteorologiche.db')
    query="select b.name as city,c.name as variable,b.x as x, b.y as y,b.z as z,c.var_id as var_id,a.time,a.value from DATA a \
    inner JOIN STATIONS b \
    on a.city_id=b.city_id \
    inner JOIN VARIABLES c on a.var_id=c.var_id "
    df=pd.read_sql(query,conn)
    df['time'] = pd.to_datetime(df['time'])

    fname = r'gadm41_ITA_1.shp'
    rdf=gpd.read_file(fname)
    ven=(rdf["NAME_1"]=='Veneto')
    venplot=rdf[ven].to_crs(3003).hvplot(color='lightgray').opts(height=600)#*plot

    mp=MeteoPlot(df)
    select_var=pn.widgets.Select(options=mp.variables,name='Variabile')
    select_agg=pn.widgets.Select(options=["max","min","median","mean","sum"],name='Raggruppa per:')
    dt_range = pn.widgets.DateRangeSlider(name='Intervallo', start=mp.df.time.min(), end=mp.df.time.max(), value=(mp.df.time.min(), mp.df.time.max()))
    #bins=pn.widgets.IntSlider(value=20,start=2,end=100,step=1,name="Bins")7
    sel_city=hv.streams.Selection1D()
    stres = dict(index=sel_city.param.index,var=select_var.param.value, time=dt_range.param.value,agg=select_agg.param.value)
    stres2 =dict(index=sel_city.param.index,var=select_var.param.value, time=dt_range.param.value)
    dmap=hv.DynamicMap(mp.get_dfq,streams=stres)
    smap=hv.DynamicMap(mp.get_series,streams=stres2)#.opts(width=600)
    hmap=hv.DynamicMap(mp.get_summary,streams=stres2)#.opts(width=600)#,shared_axes=False)
    bwmap=hv.DynamicMap(mp.get_boxwhiskers,streams=stres2)
    title="#Variabili meteorologiche mensili Veneto 1994-2022"
    tableheader=pn.pane.Markdown("Statistiche")
    top=pn.layout.WidgetBox(pn.pane.Markdown(title, margin=(0, 10)),select_var,dt_range,select_agg,width=400,height=1200,responsive=True)
    pn.Row(top,pn.Column(pn.Row(gv.tile_sources.OSM.opts(alpha=0.5)*dmap,pn.Column(pn.Column(tableheader,hmap,align='center'),bwmap)),smap)).servable()
    #pn.Row(bwmap)

main()
#if __name__=="__main__":
#    main()
