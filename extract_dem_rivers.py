#!/usr/bin/env python3
#this is the python library used to extracted river network from DEM
from pylib import *
         
class dem(object):
    def __init__(self):
        pass      
    
    def read_data(self,path):
        '''
        read data of *.npz format
        '''        
        #read data
        data=loadz(path)
        
        #get variable name
        svars=list(data.__dict__.keys())
        if 'VINFO' in svars: svars.remove('VINFO')
        
        #put variables in self
        for svar in svars:
            exec('self.{}=data.{}'.format(svar,svar))
            
    def save_data(self,fname,svars):
        '''
        save attributes of svars in *.npz format
        '''
        
        S=npz_data(); 
        for svar in svars:
            exec('S.{}=self.{}'.format(svar,svar))
        save_npz(fname,S)
    
    def read_demdata(self,outname='dem',data=None,save_bnd=True):   
        '''
        read dem raw data from info.name or data
        also save values on subdomain boundary for later combination
        '''

        info=self.info
        #read data directly                
        if data is None:            
            if info.name.endswith('.asc'):
                data=loadtxt(info.name,skiprows=info.skiprows,max_rows=info.max_rows,usecols=info.usecols)
                exec('self.{}=data'.format(outname))
        else:
            #extract data        
            rind=info.ind_read;        
            exec('self.{}=data[{}:{},{}:{}].copy()'.format(outname,*info.ind_read))
        
        #save bnd values     
        if hasattr(self,'dem'): 
            self.info.dem_bnd=self.dem.ravel()[self.info.sind_bnd].copy()
            
            #update bnd info if there is nodata
            fpn=self.info.dem_bnd!=self.info.nodata            
            if self.info.is_subdomain: self.info.sind_bnd_global=self.info.sind_bnd_global[fpn]    
            self.info.sind_bnd=self.info.sind_bnd[fpn].copy()            
            self.info.dem_bnd=self.info.dem_bnd[fpn].copy()            
        if hasattr(self,'dir'): self.info.dir_bnd=self.dir.ravel()[self.info.sind_bnd].copy()   
        
        #convert nan to nodata
        self.remove_nan(outname)
        
    def collect_subdomain_data(self,name='dem',outname='dem'):
        '''
        collect subdomain values to reconstruct global domain data
        name: attribute to be combined
        outname: name of combined global variable
        '''
        
        #initialize
        exec('self.{}=ones(self.info.ds)*self.info.nodata'.format(outname))
        
        #colloect data and also bnd dir and dem
        sind_bnd_local=[]; dem_bnd_local=[]; dir_bnd_local=[]; sind_bnd_nodata=[]
        for i in arange(self.info.nsubdomain):
            eind=self.domains[i].info.ind_extract
            cind=self.info.ind_collect[i]
            exec('self.{}[{}:{},{}:{}]=self.domains[{}].{}[{}:{},{}:{}]'.format(outname,*cind,i,name,*eind))
            
            #bnd info
            sind_bnd_local.extend(self.domains[i].info.sind_bnd_global)
            sind_bnd_nodata.extend(self.domains[i].info.sind_bnd_nodata_global)
            if hasattr(self.domains[i].info,'dir_bnd'): dir_bnd_local.extend(self.domains[i].info.dir_bnd)
            if hasattr(self.domains[i].info,'dem_bnd'): dem_bnd_local.extend(self.domains[i].info.dem_bnd)
        self.info.sind_bnd_local=array(sind_bnd_local)
        self.info.dir_bnd_local=array(dir_bnd_local)
        self.info.dem_bnd_local=array(dem_bnd_local)
        self.info.sind_bnd_nodata=unique(r_[self.info.sind_bnd_nodata,sind_bnd_nodata])
    
    def collapse_subdomain(self,svars=['dem','dir']):
        '''
        this function is used to remove outer zone of subdomain
        update on "info"
        '''
        
        if not self.info.is_subdomain: return
                
        #extract the domain data
        eind=self.info.ind_extract
        for svar in svars:
            if not hasattr(self,svar): continue
            exec('self.{}=self.{}[{}:{},{}:{}].copy()'.format(svar,svar,*eind))
        
        #update other information of subdomain
        iy1,iy2,ix1,ix2=eind; ym=iy2-iy1; xm=ix2-ix1
        yll,xll,dxy=self.info.header[2:]
        self.info.header=[ym,xm,yll-iy1*dxy,xll+ix1*dxy,dxy]
        self.info.ds=[ym,xm]
        self.info.extent=[xll+ix1*dxy,xll+(ix2-1)*dxy,yll-(iy2-1)*dxy,yll-iy1*dxy]
        self.info.skiprows=self.info.skiprows+iy1
        self.info.usecols=self.info.usecols[ix1:ix2]
        self.info.max_rows=ym
        
        #local index
        biy=r_[zeros(xm),ones(xm)*(ym-1),arange(1,ym-1),arange(1,ym-1)].astype('int')
        bix=r_[arange(xm),arange(xm),zeros(ym-2),ones(ym-2)*(xm-1)].astype('int')
        self.info.sind_bnd=ravel_multi_index([biy,bix],self.info.ds)
                
        rind=self.info.ind_read;
        self.info.ind_read=[rind[0]+iy1,rind[0]+iy1+ym,rind[2]+ix1,rind[2]+ix1+xm]
        self.info.ind_extract=[0,ym,0,xm]   
    
        #global index
        biy=biy+rind[0]+iy1; bix=bix+rind[2]+ix1
        self.info.sind_bnd_global=ravel_multi_index([biy,bix],self.info.ds_global)
        self.info.bxy_global[0]=self.info.bxy_global[0]+iy1
        self.info.bxy_global[1]=self.info.bxy_global[1]+ix1
        
        #bnd        
        if hasattr(self,'dem'): 
            self.info.dem_bnd=self.dem.ravel()[self.info.sind_bnd].copy()
            
            #update bnd info if there is nodata
            fpn=self.info.dem_bnd!=self.info.nodata            
            self.info.sind_bnd_global=self.info.sind_bnd_global[fpn]
            self.info.sind_bnd=self.info.sind_bnd[fpn].copy()            
            self.info.dem_bnd=self.info.dem_bnd[fpn].copy()            
        if hasattr(self,'dir'): self.info.dir_bnd=self.dir.ravel()[self.info.sind_bnd].copy() 
        
               
    def save_bnd_value(self):
        '''
        save bnd values of dem and dir
        '''
        
        if hasattr(self,'dem'): 
            self.info.dem_bnd=self.dem.ravel()[self.info.sind_bnd].copy()
            fpn=self.info.dem_bnd!=self.info.nodata
            self.info.sind_bnd=self.info.sind_bnd[fpn].copy()
            self.info.dem_bnd=self.info.dem_bnd[fpn].copy()            
        if hasattr(self,'dir'): self.info.dir_bnd=self.dir.ravel()[self.info.sind_bnd].copy() 
                                                         
    def read_deminfo(self,name,subdomain_size=5e6,offset=0):
        '''
        read header info, and divide the data to subdomains based on subdomain_size
        work for *asc, add other format later
        '''
        
        self.info=npz_data()
        #read header
        if name.endswith('.asc'):
            with open(name,'r') as fid:
                xm=int(fid.readline().split()[1])
                ym=int(fid.readline().split()[1])
                xll=float(fid.readline().split()[1])
                yll=float(fid.readline().split()[1])
                dxy=float(fid.readline().split()[1])
                nval=fid.readline().split()[1]
                if nval.lower() in ('nan','-nan'):
                    nodata=nan
                else:
                    nodata=float(nval)
        
        #change yll to upper left corner
        yll=yll+(ym-1)*dxy
                
        #process info
        nsize=ym*xm; 
        self.info.name=name
        self.info.header=[ym,xm,yll,xll,dxy]
        self.info.nodata=nodata
        self.info.ds=[ym,xm]; 
        # self.info.shape=[ym,xm]; 
        self.info.extent=[xll,xll+(xm-1)*dxy,yll-(ym-1)*dxy,yll]
        self.info.skiprows=6
        self.info.usecols=arange(xm).astype('int')
        self.info.max_rows=ym        
        self.info.ind_read=[0,ym,0,xm]
        
        biy=r_[zeros(xm),ones(xm)*(ym-1),arange(1,ym-1),arange(1,ym-1)].astype('int')
        bix=r_[arange(xm),arange(xm),zeros(ym-2),ones(ym-2)*(xm-1)].astype('int')
        self.info.sind_bnd=ravel_multi_index([biy,bix],self.info.ds)
        self.info.sind_bnd_nodata=array([]).astype('int')
        
        #divide the domain into subdomains       
        nsub=max(around(nsize/subdomain_size),1);         
        nx=max(int(round(sqrt(nsub))),1); ny=max(int(nsub/nx),1);
        dy0=int(floor(ym/ny)); dx0=int(floor(xm/nx))        
        
        self.info.is_subdomain=False
        self.info.nsubdomain=nx*ny; 
        self.info.subdomain_shape=[ny,nx]
        self.info.subdomain_size=[dy0,dx0]
        self.info.ind_collect=[]
        self.domains=[]

        #calcuate subdomain info        
        for i in arange(ny):
            dy00=dy0
            #subdomain index
            if ny==1:
                iy=0; dy=dy0; ylli=yll; indy=[0,dy]; cindy=[0,dy0]
            else:
                if i==0:
                    iy=0;  dy=dy0+offset;  ylli=yll; indy=[0,dy-offset]; cindy=[0,dy0]
                elif i==(ny-1):
                    iy=i*dy0-offset;  dy=ym-iy;  ylli=yll-iy*dxy;  indy=[offset,dy]; dy00=dy-offset; cindy=[i*dy0,ym]
                else:
                    iy=i*dy0-offset;  dy=dy0+2*offset;  ylli=yll-iy*dxy; indy=[offset,dy-offset]; cindy=[i*dy0,(i+1)*dy0]
            
            dx00=dx0
            for k in arange(nx):                                
                #subdomain index
                if nx==1:
                    ix=0;  dx=dx0;  xlli=xll; indx=[0,dx]; cindx=[0,dx0]
                else:
                    if k==0:
                        ix=0;  dx=dx0+offset;  xlli=xll; indx=[0,dx-offset]; cindx=[0,dx0]
                    elif k==(nx-1):
                        ix=k*dx0-offset; dx=xm-ix;  xlli=xll+ix*dxy; indx=[offset,dx]; dx00=dx-offset; cindx=[k*dx0,xm]
                    else:
                        ix=k*dx0-offset; dx=dx0+2*offset;  xlli=xll+ix*dxy; indx=[offset,dx-offset]; cindx=[k*dx0,(k+1)*dx0]
                
                #save subdomain info
                sinfo=npz_data();     
                sinfo.name=name                    
                sinfo.header=[dy,dx,ylli,xlli,dxy]
                sinfo.nodata=nodata
                sinfo.ds=[dy,dx]
                sinfo.ds_global=[ym,xm]
                sinfo.bxy_global=[iy,ix]
                # sinfo.shape=[dy00,dx00]
                sinfo.extent=[xlli,xlli+(dx-1)*dxy,ylli-(dy-1)*dxy,ylli]
                sinfo.skiprows=6+iy
                sinfo.usecols=arange(ix,ix+dx).astype('int')
                sinfo.max_rows=dy
                sinfo.is_subdomain=True
                
                #local boundary index
                biy=r_[zeros(dx),ones(dx)*(dy-1),arange(1,dy-1),arange(1,dy-1)].astype('int')
                bix=r_[arange(dx),arange(dx),zeros(dy-2),ones(dy-2)*(dx-1)].astype('int')
                sinfo.sind_bnd=ravel_multi_index([biy,bix],sinfo.ds)
                sinfo.sind_bnd_nodata=array([]).astype('int')
                
                #global boundary index
                biy=biy+iy; bix=bix+ix;
                sinfo.sind_bnd_global=ravel_multi_index([biy,bix],[ym,xm])
                sinfo.sind_bnd_nodata_global=array([]).astype('int')
                
                sinfo.ind_read=[iy,iy+dy,ix,ix+dx] #index in domain: extract domain data for subdomain
                sinfo.ind_extract=[*indy,*indx]    #index in subdomain: extract subdomain data to constrcut domain data   
                ind_collect=[*cindy,*cindx]        #index in domain: extract subdomain data to constrcut domain data   
                sinfo.nsubdomain=0
                
                sdata=dem(); sdata.info=sinfo
                self.domains.append(sdata)   
                self.info.ind_collect.append(ind_collect)
        
    def compute_river(self,seg=None,sind=None,acc_limit=1e4,nodata=None,apply_mask=False):   
        '''
        compute river network for watersheds 
        seg is segment number, sind is catchment indices. 
        '''
        
        #compute river mouths        
        if sind is not None:
            sind0=sind.copy(); seg0=self.seg.ravel()[sind0]

        if seg is not None: #may rewrite sind
            if hasattr(seg,'__len__'):
                seg=array(seg)
            else:
                seg=array([seg,])
                
            sind0=nonzero(self.dir.ravel()==0)[0]; seg0=self.seg.ravel()[sind0]
            seg_in,ia,ib=intersect1d(seg,seg0,return_indices=True)
            seg0=seg0[ib]; sind0=sind0[ib];
        
        if (sind is None) and (seg is None):
            sind0=nonzero(self.dir.ravel()==0)[0]; seg0=self.seg.ravel()[sind0]
                    
        #pre-define varibles, will update in the loop
        if nodata is None: nodata=self.info.nodata
        sind=sind0; slen=len(sind); 
        num=arange(slen).astype('int'); pind0=None; 
        
        print('computing river network')
        
        #each pts cooresponding to a river network
        self.rivers=[[] for i in arange(len(sind0))]; 
                
        while len(sind)!=0:
            #search the largest stream
            sind_list=self.search_upstream(sind,ireturn=7,acc_limit=acc_limit)
                                    
            #add rivers         
            for i in arange(slen):            
                if pind0 is not None: self.rivers[num[i]].append(pind0[i])
                self.rivers[num[i]].extend(sind_list[i])
                self.rivers[num[i]].append(self.info.nodata)
            
            #create new pind for search 
            pind=[]; pnum=[]; 
            for i in arange(slen):
                pind.extend(sind_list[i])
                pnum.extend(ones(len(sind_list[i]))*num[i])
            pind=array(pind); pnum=array(pnum).astype('int')
        
            #create new sind
            sind,pnum_ind=self.search_upstream(pind,ireturn=5,acc_limit=acc_limit)
            slen=len(sind); num=pnum[pnum_ind];  pind0=pind[pnum_ind]
                    
        #format
        inum=[]
        for i in arange(len(sind0)):
            river=array(self.rivers[i]).astype('int')            
            #apply mask
            if apply_mask:
                fpm=self.mask.ravel()[river]
                river[~fpm]=self.info.nodata
                
                #only one nodata in between
                nind=nonzero(river==self.info.nodata)[0]; dind=diff(nind); 
                fpd=nonzero(dind==1)[0]+1; nind=nind[fpd]
                
                fpn=ones(len(river)).astype('bool'); fpn[nind]=False;  
                river=river[fpn]                
                
            self.rivers[i]=river
            if len(self.rivers[i])>3: inum.append(i)
        self.rivers=array(self.rivers); inum=array(inum)
            
        #exclude rivers with len<3
        self.rivers=self.rivers[inum]
        
        #add river information to info
        self.info.rseg=seg0[inum]
        self.info.rind=sind0[inum]
            
    def compute_boundary(self,seg=None,sind=None,acc_limit=None,level_max=100):
        '''
        comtpue boundary for pts(sind) or segments(seg); seg overite sind
        '''
                
        #pre-define variables
        ds=self.info.ds; ym,xm=ds
               
        #compute river mouths        
        if sind is not None:
            sind0=sind.copy(); seg0=self.seg.ravel()[sind0]

        if seg is not None: #may rewrite sind0
            if hasattr(seg,'__len__'):
                seg=array(seg)
            else:
                seg=array([seg,])
                
            sind0=nonzero(self.dir.ravel()==0)[0]; seg0=self.seg.ravel()[sind0]
            seg_in,ia,ib=intersect1d(seg,seg0,return_indices=True)
            seg0=seg0[ib]; sind0=sind0[ib];
        
        if (sind is None) and (seg is None):
            sind0=nonzero(self.dir.ravel()==0)[0]; seg0=self.seg.ravel()[sind0]
        
        #compute watershed bnd
        sind=sind0.copy()
        
        #exclude pts with acc<acc_limit
        if acc_limit is not None:
            fpa=self.acc.ravel()[sind]>=acc_limit
            sind=sind[fpa]; seg=seg0[fpa]
                
        #---------------method 2-----------------------------------------------
        #find boundary pts        
        fps=arange(len(sind)).astype('int'); seg=self.seg.ravel()[sind]
        while len(fps)!=0:            
            #exclude pts already on domain bounday
            iy,ix=unravel_index(sind[fps],ds)
            fpb=(iy==(ym-1))|(ix==(xm-1))|(iy==0)|(ix==0)
            fps=fps[~fpb]

            #check the other three directions see whether 
            sind_next=r_[sind[fps]-xm,sind[fps]-xm-1,sind[fps]-1]
            seg_next=self.seg.ravel()[sind_next]
            
            #has next cells with same seg
            fp=seg_next==tile(seg[fps],3); sind_next[~fp]=sys.maxsize
            fpt=(fp).reshape([3,len(fps)]).sum(axis=0)!=0
            
            #reset
            sind[fps[fpt]]=sind_next.reshape([3,len(fps)]).min(axis=0)[fpt]            
            fps=fps[fpt]            
                           
        #search boundary
        self.boundary=self.search_boundary(sind,level_max=level_max)  
        
        #add boundary info        
        self.info.bseg=seg
    
    def compute_watershed(self):
        '''        
        acc_max: compute acc and segment number for all watersheds
        '''
        
        if not hasattr(self,'dir'): sys.exit('dir not exist')

        #all the catchments        
        sind0=nonzero(self.dir.ravel()==0)[0];         
        
        print('---------compute watershed------------------------------------')
        #initialize acc        
        self.search_upstream(sind0,ireturn=3,level_max=100)
        
        print('---------sort watershed number--------------------------------')
        #reorder segment number
        acc0=self.acc.ravel()[sind0]; ind=flipud(argsort(acc0)); sind=sind0[ind]; 
        seg=arange(len(sind)).astype('int')+1
        self.search_upstream(sind,ireturn=3,seg=seg,level_max=100) 
        
        return
                                
    def compute_dir(self,data='dem',outname='dir',subdomain_size=1e5,zlimit=0,method=0):
        '''
        when diff(dem)<zlimit, regard them the same elevation
        method=0: don't assign dir to flat cells; 
        method=1: assign dir to flat cells
        method=2: don't compute dir on boundary
        '''
        
        #dem data
        if type(data)==str: #assume data is dem  
            # if not hasattr(self,'ds'): self.ds=self.dem.shape
            
            #change dem dimension
            self.dem=self.dem.ravel()
            dem0=self.dem
        else:
            dem0=data.ravel()
            
        #pre-calculation                
        ds=self.info.ds; ym,xm=ds; nsize=prod(ds); nlim=subdomain_size
        dir=zeros(nsize).astype('int32'); nodata=self.info.nodata
        nsubdomain=int(max(round(nsize/nlim),1))
                    
        offsets_all=array([1,-xm,-1,xm, -xm+1,-xm-1,xm-1,xm+1])
        ndirs_all=array([1, 64, 16, 4, 128, 32, 8,  2])
        pdirs_all=array([16, 4,  1, 64, 8,   2, 128,32])
           
        if method==2:
            nloop=1
        else:
            nloop=3
        #calculate dir for each subdomain      
        for it in arange(nloop):
            if it==0: 
                nsub=nsubdomain #for subdomain
            else:
                nsub=4 #for 4 sides and 4 corners   

            #for each section   
            for i in arange(nsub):
                if it==0:
                    #get index for subdomain
                    if i==(nsub-1):
                        sind0=arange(i*nlim,nsize).astype('int')
                    else:
                        sind0=arange(i*nlim,(i+1)*nlim).astype('int')
                    
                    #exclude pts on boundary
                    iy,ix=unravel_index(sind0,ds)
                    fp=(ix>0)*(ix<(xm-1))*(iy>0)*(iy<(ym-1)); sind0=sind0[fp]
                    
                    flag=arange(8)
                elif it==1:
                    #get index for each side
                    if i==0:
                        sind0=arange(1,xm-1);                       
                        flag=array([0,2,3,6,7 ])
                    elif i==1:
                        sind0=arange(1,xm-1)+(ym-1)*xm; 
                        flag=array([0,1,2,4,5])
                    elif i==2:
                        sind0=arange(1,ym-1)*xm
                        flag=array([0,1,3,4,7])
                    elif i==3:
                        sind0=arange(1,ym-1)*xm+(xm-1)                        
                        flag=array([1,2,3,5,6])
                    dir[sind0]=0
                elif it==2:
                    #get index for each corner
                    if i==0:
                        sind0=array([0])
                        flag=array([0,3,7])
                    elif i==1:
                        sind0=array([xm-1])                        
                        flag=array([2,3,6])
                    elif i==2:
                        sind0=array([(ym-1)*xm])
                        flag=array([0,1,4])
                    elif i==3:
                        sind0=array([nsize-1])                        
                        flag=array([1,2,5])
                    dir[sind0]=0
                                                
                #begin compute dir-----------------------------------------------
                #define offsets for each sid-e
                offsets=offsets_all[flag]
                ndirs=ndirs_all[flag]
                #pdirs=pdirs_all[flag]
                               
                #exclude nodata
                sdem=dem0[sind0]; 
                fp=sdem!=nodata; dir[sind0[~fp]]=-1                
                sind=sind0[fp]; dem=sdem[fp];  slen=sum(fp)
                if len(sind)==0: continue
                    
                #find the neighbor with min. depth
                ndem=ones(slen)*nodata; nind=zeros(slen).astype('int');  ndir=nind.copy() # pdir=nind.copy()
                for m in arange(len(offsets)):
                    sindi=sind+offsets[m]; 
                    fpo=sindi>=nsize; sindi[fpo]=nsize-1
                    demi=dem0[sindi]
                    
                    #check values
                    fpm1=(demi!=nodata)*(ndem==nodata)
                    fpm2=(demi!=nodata)*(ndem!=nodata)*(demi<ndem)
                    fpm=fpm1|fpm2                    
                        
                    #assign new ndem if ndem==nodata and demi!=nodata, and if demi<ndem            
                    nind[fpm]=sindi[fpm]
                    ndem[fpm]=demi[fpm]
                    ndir[fpm]=ndirs[m]
                    #pdir[fpm]=pdirs[m]
                                     
                #when dem>ndem
                fpm=(ndem!=nodata)*(dem>(ndem+zlimit))                
                dir[sind[fpm]]=ndir[fpm]
                
                #when dem=ndem, assign dir first
                if method==1:
                    fpm=(ndem!=nodata)*(abs(dem-ndem)<=zlimit)*(sind<nind)
                    dir[sind[fpm]]=ndir[fpm]
        
        #make sure dir=-1 for nodata
        dir[dem0==nodata]=-1
        
        #convert nodata to nan
        if isnan(self.info.nodata): dem0[fpn]=self.info.nodata
        if type(data)==str: self.dem=self.dem.reshape(ds) #assume data is dem
                                                        
        #reshape
        dir=dir.reshape(ds)
        exec('self.{}=dir'.format(outname)) 
    
    def change_bnd_dir(self):
        '''
        let dir=0 if dir on the boundary is outflow
        '''
        
        ds=self.info.ds; ym,xm=ds
        
        #bnd info
        sind_bnd=self.info.sind_bnd        
        dir_bnd=self.dir.ravel()[sind_bnd]
        iy,ix=unravel_index(sind_bnd,ds)
        
        #dirs on four sides
        dirs=[[32,64,128],[2,4,8],[8,16,32],[1,2,128]]
        #inds=[arange(1,xm-1),xm+arange(1,xm-1),2*xm+arange(0,ym-2),2*xm+(ym-2)+arange(0,ym-2)]
        for i in arange(4):
            if i==0:
                fpr=(iy==0)*(ix>0)*(ix<(xm-1))
            elif i==1:
                fpr=(iy==(ym-1))*(ix>0)*(ix<(xm-1))
            elif i==2:
                fpr=(ix==0)*(iy>0)*(iy<(ym-1))
            elif i==3:
                fpr=(ix==(xm-1))*(iy>0)*(iy<(ym-1))
            
            fpr=nonzero(fpr)[0]; diri=dir_bnd[fpr]
            fpd=nonzero((diri==dirs[i][0])|(diri==dirs[i][1])|(diri==dirs[i][2]))[0]
            self.dir.ravel()[sind_bnd[fpr[fpd]]]=0
            
        #dirs on four corners
        dirs=[[1,2,4],[4,8,16],[1,128,64],[16,32,64]]
        #inds=[0,xm-1,xm,2*xm-1]
        for i in arange(4):
            if i==0:
                fpr=(iy==0)*(ix==0)
            elif i==1:
                fpr=(iy==0)*(ix==(xm-1))
            elif i==2:
                fpr=(iy==(ym-1))*(ix==0)
            elif i==3:
                fpr=(iy==(ym-1))*(ix==(xm-1))
            fpr=nonzero(fpr)[0]; diri=dir_bnd[fpr]
            if len(diri)==0: continue
            if (diri!=dirs[i][0])*(diri!=dirs[i][1])*(diri!=dirs[i][2]):
                self.dir.ravel()[sind_bnd[fpr]]=0        
        
    def fill_depression(self,level_max=100,method=0):
        '''
        method=0: resolve all flats 
        method=1: don't resolve flats on boundary (dir=0)
        method=2: resolve data when only self.info.dem_bnd_local is available, and no self.dem
        '''

        #pre-define variables       
        ds=self.info.ds; ym,xm=ds
                
        #initialize
        sind0=nonzero(self.dir.ravel()==0)[0]; iy,ix=unravel_index(sind0,ds)
        fp=(ix>0)*(ix<(xm-1))*(iy>0)*(iy<(ym-1)); sind0=setdiff1d(sind0[fp],self.info.sind_bnd_nodata)
        if sind0.size==0: return        
                
        #resolve flats         
        if method==0:
            print('---------resolve DEM flats------------------------------------')
            isum=self.search_upstream(sind0,ireturn=2)
            self.resolve_flat(sind0[isum==0])    
        
        #resolve flats for single cells
        # sind0=nonzero(self.dir.ravel()==0)[0]
        # if method==1:
        #     iy,ix=unravel_index(sind0,ds)
        #     fp=(ix>0)*(ix<(xm-1))*(iy>0)*(iy<(ym-1)); sind0=sind0[fp]        
        # isum=self.search_upstream(sind0,ireturn=2)    
        # self.search_flat(sind0[isum==0],ireturn=6)
              
        #identify depression catchment
        sind0=nonzero(self.dir.ravel()==0)[0]; iy,ix=unravel_index(sind0,ds)
        fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); sind0=setdiff1d(sind0[fp],self.info.sind_bnd_nodata)
        if sind0.size==0: return
        
        #search and mark each depression
        print('---------identify and mark depressions------------------------')
        slen=len(sind0); seg0=arange(slen)+1; h0=self.dem.ravel()[sind0];  
        self.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max)
        
        #get indices for each depression; here seg is numbering, not segment number
        print('---------save all depression points---------------------------')
        sind_segs=self.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=level_max)
        ns0=array([len(i) for i in sind_segs])                  
      
        #get depression boundary
        print('---------compute depression boundary--------------------------')
        self.compute_boundary(sind=sind0); 
            
        #loop to reverse dir along streams
        print('---------fill depressions-------------------------------------')
        ids=arange(slen); iflag=0
        while len(sind0)!=0:
            iflag=iflag+1
            print('fill depression: loop={}, ndep={}'.format(iflag,slen))
            # slen=len(ids); h0=h00[ids]; sind0=sind00[ids]; ns0=ns00[ids]
            # ids=arange(slen)
            #-------------------------------------------------------------------------
            #seg0,     ns0,     h0,      sind0,       sind_bnd,   h_bnd
            #seg_min,  ns_min,  h0_min,  sind0_min,   sind_min,   h_min  h_bnd_min  dir_min
            #-------------------------------------------------------------------------        
            
            #exclude nonboundary indices
            sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
            for i in arange(slen):            
                sindi=unique(self.boundary[i]); id2=id1+len(sindi)
                sind_bnd_all.extend(sindi)        
                ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)                         
            sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd)
            flag_bnd_all=self.search_flat(sind_bnd_all,ireturn=10)
            for i in arange(slen):
                self.boundary[i]=sind_bnd_all[ids_bnd[i][flag_bnd_all[ids_bnd[i]]]]
                
            #recalcuate bnd for seg with false boundary
            len_seg=array([len(i) for i in sind_segs]); 
            len_bnd=array([len(i) for i in self.boundary])
            idz=nonzero((len_bnd==0)*(len_seg!=0))[0]
            if len(idz)!=0:
                #save boundary first
                boundary=self.boundary.copy(); delattr(self,'boundary')
                self.compute_boundary(sind=sind0[idz]);
                if len(idz)==1:
                    boundary[idz[0]]=self.boundary[0]
                else:
                    boundary[idz]=self.boundary
                    
                self.boundary=boundary; boundary=None
                                        
            #rearange the boundary index
            sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
            for i in arange(slen):            
                sindi=self.boundary[i]; id2=id1+len(sindi)
                sind_bnd_all.extend(sindi)        
                ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)             
            sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd);
            
            #find all the neighboring indices with minimum depth
            sind_min_all,h_min_all,dir_min_all=self.search_flat(sind_bnd_all,ireturn=8)
                    
            #minimum for each seg
            h_min=array([h_min_all[id].min() for id in ids_bnd])
            mind=array([nonzero(h_min_all[id]==hi)[0][0] for id,hi in zip(ids_bnd,h_min)])        
            sind_bnd=array([sind_bnd_all[id][mi] for id,mi in zip(ids_bnd,mind)]); h_bnd=self.dem.ravel()[sind_bnd]
            sind_min=array([sind_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
            dir_min=array([dir_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
            
            #get s0_min,h0_min,sind0_min
            seg_min=self.seg.ravel()[sind_min]; fps=nonzero(seg_min!=0)[0]; 
                    
            ind_sort=argsort(seg_min[fps]);  
            seg_1, ind_unique=unique(seg_min[fps[ind_sort]],return_inverse=True)
            seg_2,iA,iB=intersect1d(seg_1,seg0,return_indices=True)        
            ids_min=zeros(slen).astype('int'); ids_min[fps[ind_sort]]=ids[iB][ind_unique]
            
            ns_min=zeros(slen).astype('int');    ns_min[fps]=ns0[ids_min[fps]]
            h0_min=-1e5*ones(slen);              h0_min[fps]=h0[ids_min[fps]]
            sind0_min=-ones(slen).astype('int'); sind0_min[fps]=sind0[ids_min[fps]]
            h_bnd_min=zeros(slen);               h_bnd_min[fps]=h_bnd[ids_min[fps]]
        
            #get stream from head to catchment
            fp1=seg_min==0; 
            fp2=(seg_min!=0)*(h0_min<h0); 
            fp3=(seg_min!=0)*(h0_min==h0)*(ns_min>ns0)
            fp4=(seg_min!=0)*(h0_min==h0)*(ns_min==ns0)*(h_bnd>h_bnd_min); 
            fp5=(seg_min!=0)*(h0_min==h0)*(ns_min==ns0)*(h_bnd==h_bnd_min)*(sind0>sind0_min);         
            fph=nonzero(fp1|fp2|fp3|fp4|fp5)[0]; sind_head=sind_bnd[fph];
            if len(fph)==0: 
                #sind0 is on the boundary bounded by nodata
                #local 
                self.info.sind_bnd=r_[self.info.sind_bnd,sind0]                
                self.info.sind_bnd_nodata=r_[self.info.sind_bnd_nodata, sind0]
                if hasattr(self.info,'dir_bnd'): self.info.dir_bnd=r_[self.info.dir_bnd,self.dir.ravel()[sind0]]
                if hasattr(self.info,'dem_bnd'): self.info.dem_bnd=r_[self.info.dem_bnd,self.dem.ravel()[sind0]]  
                #global
                if self.info.is_subdomain:
                    biy,bix=unravel_index(sind0,ds); biy=biy+self.info.bxy_global[0]; bix=bix+self.info.bxy_global[1]; 
                    sind_bnd_global=ravel_multi_index([biy,bix],self.info.ds_global)
                    self.info.sind_bnd_global=r_[self.info.sind_bnd_global, sind_bnd_global]
                    self.info.sind_bnd_nodata=r_[self.info.sind_bnd_nodata, sind_bnd_global]
                    self.info.sind_bnd_nodata_global=r_[self.info.sind_bnd_nodata_global, sind_bnd_global]                
                break            
            sind_streams=self.search_downstream(sind_head,ireturn=2,msg=False)        
                    
            #get all stream index and its dir
            sind=[]; dir=[];
            for i in arange(len(fph)):
                id=fph[i];    
                #S.seg.ravel()[sind_segs[id]]=seg_min[id]; seg0[id]=seg_min[id]
                sind_stream=sind_streams[i]
                dir_stream=r_[dir_min[id],self.dir.ravel()[sind_stream][:-1]]            
                sind.extend(sind_stream); dir.extend(dir_stream)
            sind=array(sind); dir0=array(dir).copy(); dir=zeros(len(dir0)).astype('int')
                
            #reverse dir
            dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
            for i in arange(8):
                fpr=dir0==dir_0[i]; dir[fpr]=dir_inv[i]    
            self.dir.ravel()[sind]=dir;
               
            #----build the linkage--------------------------------------------------
            s_0=seg0.copy(); d_0=seg_min.copy(); d_0[setdiff1d(arange(slen),fph)]=-1
            while True:         
                fpz=nonzero((d_0!=0)*(d_0!=-1))[0] 
                if len(fpz)==0: break         
            
                #assign new value of d_0
                s1=d_0[fpz].copy(); 
                            
                ind_sort=argsort(s1); 
                s2,ind_unique=unique(s1[ind_sort],return_inverse=True)
                s3,iA,iB=intersect1d(s2,s_0,return_indices=True)            
                d_0[fpz[ind_sort]]=d_0[iB[ind_unique]]
                
                #assign new value fo s_0
                s_0[fpz]=s1;
            
            #--------------------------
            seg_stream=seg0[fph[d_0[fph]==-1]] #seg that flows to another seg (!=0)        
            seg_tmp,iA,sid=intersect1d(seg_stream,seg0,return_indices=True)
            
            seg_target=s_0[fph[d_0[fph]==-1]]; tid=zeros(len(seg_target)).astype('int'); 
            ind_sort=argsort(seg_target); seg_tmp, ind_unique=unique(seg_target[ind_sort],return_inverse=True)
            seg_tmp,iA,iB=intersect1d(seg_target,seg0,return_indices=True);
            tid[ind_sort]=iB[ind_unique]
            #----------------------------------------------------------------------
                        
            #reset variables-----
            ids_stream=ids[fph]; ids_left=setdiff1d(ids,ids_stream)        
    
            #collect boundary        
            for si,ti in zip(sid,tid):                        
                self.seg.ravel()[sind_segs[si]]=seg0[ti]
                self.boundary[ti]=r_[self.boundary[ti],self.boundary[si]]
                sind_segs[ti]=r_[sind_segs[ti],sind_segs[si]]
                ns0[ti]=ns0[ti]+ns0[si]
                   
            #set other seg number to zeros
            seg_stream2=seg0[fph[d_0[fph]==0]] #seg that flows to another seg (!=0)        
            seg_tmp,iA,sid2=intersect1d(seg_stream2,seg0,return_indices=True)
            for si in sid2:
                self.seg.ravel()[sind_segs[si]]=0
            
            #update variables    
            sind0=sind0[ids_left]; seg0=seg0[ids_left]; h0=h0[ids_left]; ns0=ns0[ids_left]
            self.boundary=self.boundary[ids_left]; sind_segs=sind_segs[ids_left]
            slen=len(sind0); ids=arange(slen)
        #clean
        delattr(self,'seg');delattr(self,'boundary')
        
    def fill_depression_global(self,level_max=100):
        '''
        method=0: resolve depression without DEM data
        '''
        print('--------------------------------------------------------------')
        print('---------work on global domain depression---------------------')
        print('--------------------------------------------------------------')
        
        #pre-define variables       
        ds=self.info.ds; ym,xm=ds
        
        #this part assign dir directly if the original dir of boundary cells is not zero
        sind0=self.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds); 
        fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); sind0=sind0[fp]
        dem0=self.info.dem_bnd_local[fp]; dir0=self.info.dir_bnd_local[fp]; #original
        dir=self.dir.ravel()[sind0] #at present
        
        #exclude nodata bnd pts
        if len(self.info.sind_bnd_nodata)!=0:
            sind_bnd_nodata,iA,iB=intersect1d(sind0,self.info.sind_bnd_nodata,return_indices=True)
            fp=setdiff1d(arange(len(sind0)),iA)
            sind0=sind0[fp]; dem0=dem0[fp]; dir0=dir0[fp]; dir=dir[fp]
        
        print('---------assign dir directly if original dir is not zero------')
        #put flow into another seg if its original dir is not zero, it doesn't form loops    
        fpz=nonzero((dir0!=0)*(dir==0))[0]; 
        self.dir.ravel()[sind0[fpz]]=dir0[fpz]
        
        #excude pts that forms loops          
        sind_list,flag_loop=self.search_downstream(sind0[fpz],ireturn=3,msg=False); 
        fpl=nonzero(flag_loop==1)[0]; sindl=sind0[fpz[fpl]]; deml=dem0[fpz[fpl]] 
        sind_list=array([intersect1d(sindl,i) for i in sind_list[fpl]])   
        sind_all=[]; ids=[]; id1=0; id2=0;  
        for i in arange(len(fpl)):            
            sindi=unique(sind_list[i]); id2=id1+len(sindi)
            sind_all.extend(sindi)        
            ids.append(arange(id1,id2).astype('int')); id1=id1+len(sindi) 
        sind_all=array(sind_all)
        sindu,fpu=unique(sind_all,return_inverse=True); sindc,iA,iB=intersect1d(sindu,sindl,return_indices=True)
        if not array_equal(sindu,sindc): sys.exit('sindc!=sindu') 
        dem_all=deml[iB][fpu]
        sind_min=unique(array([sind_all[id[nonzero(dem_all[id]==min(dem_all[id]))[0]]] for id in ids]))
        self.dir.ravel()[sind_min]=0
        
        # self.fill_depression(method=1)
        # return
        
        print('---------assign dir to neighboring segs if possible-----------')
        #this loop part assigns dir to neighboring segs of dir=0
        iflag=0
        while True:      
            iflag=iflag+1
            #identify depression catchment
            sind0=self.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
            fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(self.dir.ravel()[sind0]==0); 
            sind0=sind0[fp]; h0=self.info.dem_bnd_local[fp]
            
            #exclude nodata bnd pts
            if len(self.info.sind_bnd_nodata)!=0:
                sind_bnd_nodata,iA,iB=intersect1d(sind0,self.info.sind_bnd_nodata,return_indices=True)
                fp=setdiff1d(arange(len(sind0)),iA)
                sind0=sind0[fp]; h0=h0[fp]; 
                                                             
            #search and mark each depression            
            slen=len(sind0); seg0=arange(slen)+1
            self.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max,msg=False)
            print('fill depression: loop={}, ndep={}'.format(iflag,slen))
            
            #find all the neighboring indices with minimum depth seg 
            sind_min,sind0_min,h0_min, dir_min=self.search_flat(sind0,ireturn=8,method=1)        
            if sum(sind_min!=0)==0: break        
            #reverse dir first
            dir_min0=dir_min.copy(); dir_min[:]=0
            dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
            for i in arange(8):
                fpr=dir_min0==dir_0[i]; dir_min[fpr]=dir_inv[i] 
                
            #assign dir to the nearest seg with minimum depth; if h0=h0_min, use smaller sind0     
            fpm=nonzero(((h0>h0_min)*(sind_min!=0))|((h0==h0_min)*(sind_min!=0)*(sind0<sind0_min)))[0]
            if len(fpm)==0: fpm=nonzero((h0==h0_min)*(sind_min!=0)*(sind0>sind0_min))[0]
            if len(fpm)==0: break
            self.dir.ravel()[sind0[fpm]]=dir_min[fpm]
            sind_list,flag_loop=self.search_downstream(sind0[fpm],ireturn=3)
            if sum(flag_loop!=0)!=0: sys.exit('loop found: impossible')    
        
        if hasattr(self,'dem'): 
            self.fill_depression(method=1)
        else:
            pass
        
        return
                
        #--------------fill depression in global-------------------------------                
        #identify depression catchment
        sind0=self.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
        fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(self.dir.ravel()[sind0]==0); 
        sind0=sind0[fp]; h0=self.info.dem_bnd_local[fp]
                            
        #search and mark each depression
        print('---------identify and mark depressions------------------------')
        slen=len(sind0); seg0=arange(slen)+1
        self.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max)
        
        #get indices for each depression; here seg is numbering, not segment number
        print('---------save all depression points---------------------------')
        sind_segs=self.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=level_max)
        ns0=array([len(i) for i in sind_segs])
                     
        #get depression boundary
        print('---------compute depression boundary--------------------------')
        self.compute_boundary(sind=sind0); 
        # self.boundary=[array([i]) for i in sind0]
                              
        #loop to reverse dir along streams
        print('---------fill depressions-------------------------------------')
        ids=arange(slen); iflag=0
        while len(sind0)!=0:
            iflag=iflag+1
            print('fill depression: loop={}, ndep={}'.format(iflag,slen))
            #-------------------------------------------------------------------------
            #seg0,     ns0,     h0,      sind0,       sind_bnd
            #seg_min,  ns_min,  h0_min,  sind0_min,   sind_min
            #-------------------------------------------------------------------------        
            
            #exclude nonboundary indices
            sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
            for i in arange(len(sind0)):            
                sindi=unique(self.boundary[i]); id2=id1+len(sindi)
                sind_bnd_all.extend(sindi)        
                ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)                         
            sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd)
            flag_bnd_all=self.search_flat(sind_bnd_all,ireturn=10)
            for i in arange(slen):
                self.boundary[i]=sind_bnd_all[ids_bnd[i][flag_bnd_all[ids_bnd[i]]]]
                               
            #recalcuate bnd for seg with false boundary; caused by some segs resides some other segs
            len_seg=array([len(i) for i in sind_segs]); 
            len_bnd=array([len(i) for i in self.boundary])
            idz=nonzero((len_bnd==0)*(len_seg!=0))[0]
            if len(idz)!=0:
                #save boundary first
                boundary=self.boundary.copy(); delattr(self,'boundary')
                self.compute_boundary(sind=sind0[idz]);
                boundary[idz]=self.boundary
                self.boundary=boundary; boundary=None
            
            #rearange the boundary index
            sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
            for i in arange(len(sind0)):            
                sindi=self.boundary[i]; id2=id1+len(sindi)
                sind_bnd_all.extend(sindi)        
                ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)             
            sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd);
            
            #find the shorest route        
            len_stream=self.search_downstream(sind_bnd_all,ireturn=4,msg=False)
            for i in arange(slen):
                ind_sort=argsort(len_stream[ids_bnd[i]])
                sind_bnd_all[ids_bnd[i]]=sind_bnd_all[ids_bnd[i][ind_sort]]
                    
            #find all the neighboring indices with minimum depth seg 
            sind_min_all,sind0_min_all,h0_min_all, dir_min_all=self.search_flat(sind_bnd_all,ireturn=8,method=1)
                            
            #seg with minimum depth
            h0_min=array([h0_min_all[id].min() for id in ids_bnd])        
            mind=array([nonzero(h0_min_all[id]==hi)[0][0] for id,hi in zip(ids_bnd,h0_min)])        
            sind_bnd=array([sind_bnd_all[id][mi] for id,mi in zip(ids_bnd,mind)]); 
            sind_min=array([sind_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
            sind0_min=array([sind0_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
            dir_min=array([dir_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
            seg_min=S.seg.ravel()[sind_min]; fps=nonzero(seg_min!=0)[0]; 
                        
            #to find ns_min
            ind_sort=argsort(seg_min[fps]);  
            seg_1, ind_unique=unique(seg_min[fps[ind_sort]],return_inverse=True)
            seg_2,iA,iB=intersect1d(seg_1,seg0,return_indices=True)        
            ids_min=zeros(slen).astype('int'); ids_min[fps[ind_sort]]=ids[iB][ind_unique]
            ns_min=zeros(slen).astype('int');    ns_min[fps]=ns0[ids_min[fps]]
                 
            #get stream from head to catchment
            fp1=h0_min<h0
            fp2=(h0_min>=h0)*(seg_min==0)
            fp3=(h0_min>=h0)*(seg_min!=0)*(ns_min>ns0)
            fp4=(h0_min>=h0)*(seg_min!=0)*(ns_min==ns0)*(sind0>sind0_min)        
            fph=nonzero(fp1|fp2|fp3|fp4)[0]; sind_head=sind_bnd[fph]; 
            sind_streams=self.search_downstream(sind_head,ireturn=2,msg=False)        
            
            #get all stream index and its dir
            sind=[]; dir=[];
            for i in arange(len(fph)):
                id=fph[i];    
                #S.seg.ravel()[sind_segs[id]]=seg_min[id]; seg0[id]=seg_min[id]
                sind_stream=sind_streams[i]
                dir_stream=r_[dir_min[id],S.dir.ravel()[sind_stream][:-1]]            
                sind.extend(sind_stream); dir.extend(dir_stream)
            sind=array(sind); dir0=array(dir).copy(); dir=zeros(len(dir0)).astype('int')
                
            #reverse dir
            dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
            for i in arange(8):
                fpr=dir0==dir_0[i]; dir[fpr]=dir_inv[i]
            self.dir.ravel()[sind]=dir;
                    
            #----build the linkage--------------------------------------------------
            s_0=seg0.copy(); d_0=seg_min.copy(); d_0[setdiff1d(arange(slen),fph)]=-1
            while True:         
                fpz=nonzero((d_0!=0)*(d_0!=-1))[0] 
                if len(fpz)==0: break         
            
                #assign new value of d_0
                s1=d_0[fpz].copy(); 
                            
                ind_sort=argsort(s1); 
                s2,ind_unique=unique(s1[ind_sort],return_inverse=True)
                s3,iA,iB=intersect1d(s2,s_0,return_indices=True)            
                d_0[fpz[ind_sort]]=d_0[iB[ind_unique]]
                
                #assign new value fo s_0
                s_0[fpz]=s1;
            
            #--------------------------
            seg_stream=seg0[fph[d_0[fph]==-1]] #seg that flows to another seg (!=0)        
            seg_tmp,iA,sid=intersect1d(seg_stream,seg0,return_indices=True)
            
            seg_target=s_0[fph[d_0[fph]==-1]]; tid=zeros(len(seg_target)).astype('int'); 
            ind_sort=argsort(seg_target); seg_tmp, ind_unique=unique(seg_target[ind_sort],return_inverse=True)
            seg_tmp,iA,iB=intersect1d(seg_target,seg0,return_indices=True);
            tid[ind_sort]=iB[ind_unique]
            #----------------------------------------------------------------------
                        
            #reset variables-----
            ids_stream=ids[fph]; ids_left=setdiff1d(ids,ids_stream)        
        
            #collect boundary        
            for si,ti in zip(sid,tid):                        
                self.seg.ravel()[sind_segs[si]]=seg0[ti]
                self.boundary[ti]=r_[S.boundary[ti],self.boundary[si]]
                sind_segs[ti]=r_[sind_segs[ti],sind_segs[si]]
                ns0[ti]=ns0[ti]+ns0[si]
                   
            #set other seg number to zeros
            seg_stream2=seg0[fph[d_0[fph]==0]] #seg that flows to another seg (!=0)        
            seg_tmp,iA,sid2=intersect1d(seg_stream2,seg0,return_indices=True)
            for si in sid2:
                self.seg.ravel()[sind_segs[si]]=0
            
            #update variables    
            sind0=sind0[ids_left]; seg0=seg0[ids_left]; h0=h0[ids_left]; ns0=ns0[ids_left]
            self.boundary=self.boundary[ids_left]; sind_segs=sind_segs[ids_left]
            slen=len(sind0); ids=arange(slen)
        #clean
        delattr(self,'seg');delattr(self,'boundary')

           
    def resolve_flat(self,sind0=None,zlimit=0):
        '''
        resolve flat based on following paper
        An Efficient Assignment of Drainage Direction Over Flat Surfaces In 
        Raster Digital Elevation Models". Computers & Geosciences. doi:10.1016/j.cageo.2013.01.009"
        '''
        
        #pre-define variables
        ds=self.info.ds; ym,xm=ds; nsize=ym*xm
        
        #find indices with (dir==0)
        if sind0 is None:
            sind0=nonzero(self.dir.ravel()==0)[0]       
        
        #exclude boundary pts
        iy,ix=unravel_index(sind0,ds)
        fp=(ix>0)*(ix<(xm-1))*(iy>0)*(iy<(ym-1)); sind0=sind0[fp]
        if sind0.size==0: return
        
        #return how many neighboring indices with same elevation
        isum=self.search_flat(sind0,ireturn=1,zlimit=zlimit) #indices of flat
        fp=isum>0; sind0=sind0[fp]
        
        #obtain flat cell indices
        sind_flat=self.search_flat(sind0,ireturn=3,zlimit=zlimit); #sind_flat=unique(sind_flat)
        dir_flat0=self.dir.ravel()[sind_flat];
        
        #find the low edges
        fpl=dir_flat0!=0; sind_low=sind_flat[fpl]
        
        #find the high edges
        fp=dir_flat0==0; sind_high=self.search_flat(sind_flat[fp],ireturn=2,zlimit=zlimit); 
                
        #initialize new dem, and assing dem begining from high edges        
        dem_high=self.search_flat(sind_high,ireturn=4,zlimit=zlimit)[sind_flat]        
                         
        #initialize new dem, and assing dem begining from low edges        
        dem_low=self.search_flat(sind_low,ireturn=5,zlimit=zlimit)[sind_flat]
                        
        #combine dem_high and dem_low 
        dem_new=2*dem_low+dem_high
        
        #calcuate dir for sind_flat
        dir_flat=self.search_flat(sind_flat,ireturn=9,zlimit=zlimit,dem_flat=dem_new)
        dir_flat[fpl]=dir_flat0[fpl]; self.dir.ravel()[sind_flat]=dir_flat
        
    def search_flat(self,sind0,ireturn=0,zlimit=0,wlevel=0,level=0,level_max=100,dem_flat=None,method=0,msg=True):
        '''
        ireturn=0: return one-level nearby indices with same elevation
        ireturn=1: return how many neighboring indices with same elevation        
        ireturn=2: return high edges of flat
        ireturn=3: return all the nearby indice with same elevation (all the cells in flat)   
        ireturn=4: calculate elevation from high edges
        ireturn=5: calculate elevation from low edges
        ireturn=6: assign dir to neighboring cells that is with dir=0 & without upstream cells
        ireturn=7: return neighboring indices in seg==0 & with minimum depth.
        ireturn=8: return neighboring indices in neighboring seg & with minimum depth &dir
                   method=1 means no dem available
        ireturn=9: compute and return dir in sind_flat region based on dem_flat
        ireturn=10: return flags (True for seg-boundary cells; False for non-seg-boundary cells) 
        '''
        
        #pre-define variables
        slen=len(sind0); ds=self.info.ds; ym,xm=ds; nsize=ym*xm
        if hasattr(self,'dem'): dem0=self.dem.ravel()[sind0]
        
        #convert index
        iy0,ix0=unravel_index(sind0,ds)
        
        #construct maxtrix for neighbor
        #yind=r_[iy0-1,iy0-1,iy0-1,iy0,iy0+1,iy0+1,iy0+1,iy0]
        #xind=r_[ix0+1,ix0,ix0-1,ix0-1,ix0-1,ix0,ix0+1,ix0+1]        
        yind=r_[iy0,  iy0-1, iy0,  iy0+1, iy0-1,iy0-1, iy0+1, iy0+1]
        xind=r_[ix0+1,ix0,   ix0-1,ix0,   ix0+1,ix0-1, ix0-1, ix0+1]
        
        #true neighbors
        fpt=nonzero((xind>=0)*(xind<xm)*(yind>=0)*(yind<ym))[0]
        sind_true=ravel_multi_index([yind[fpt],xind[fpt]],ds);
        fptt=self.dir.ravel()[sind_true]!=-1; fpt=fpt[fptt]; sind_true=sind_true[fptt]
        if hasattr(self,'dem'): dem_true=self.dem.ravel()[sind_true]
        
        if ireturn==6:
            #get neighboring minimum dem and indices
            fp=dem_true==self.info.nodata;  dem_true[fp]=1e5
            dem=ones([8,slen])*1e5; dem.ravel()[fpt]=dem_true            
            iy_min=argmin(dem,axis=0); dem_min=dem[iy_min,arange(slen)]            
            
            #modify sind0's dir and dem
            #dir0=array([128,64,32,16,8,4,2,1])
            dir0=array([1,64,16,4, 128,32,8,2])
            self.dir.ravel()[sind0]=dir0[iy_min]
            self.dem.ravel()[sind0]=dem_min
            
        if ireturn==7:
            #get neighboring minimum dem and indices in seg=0
            fp=(self.seg.ravel()[sind_true]!=0)|(dem_true==self.info.nodata); dem_true[fp]=1e5;
            dem=ones([8,slen])*1e5; dem.ravel()[fpt]=dem_true
            
            sind=zeros([8,slen]).astype('int'); sind.ravel()[fpt]=sind_true
            iy_min=argmin(dem,axis=0);             
            sind_min=sind[iy_min,arange(slen)]; dem_min=dem[iy_min,arange(slen)];             
            return sind_min, dem_min
        
        if ireturn==8:          
            #get neighboring minimum dem and indices in seg=0           
            dir=tile(array([16,4,1,64,8,2,128,32]),slen).reshape([slen,8]).T            
            seg_true=self.seg.ravel()[sind_true]; seg0=self.seg.ravel()[sind0]
            
            if method==0:
                fp=(seg_true==tile(seg0,8)[fpt])|(dem_true==self.info.nodata); dem_true[fp]=1e5;
                dem=ones([8,slen])*1e5; dem.ravel()[fpt]=dem_true                
                sind=zeros([8,slen]).astype('int'); sind.ravel()[fpt]=sind_true
                
                iy_min=argmin(dem,axis=0);             
                sind_min=sind[iy_min,arange(slen)]; 
                dem_min=dem[iy_min,arange(slen)];
                dir_min=dir[iy_min,arange(slen)]; 
                return sind_min,dem_min,dir_min                    
            elif method==1:
                #find depth for sindn based on self.info.dem_bnd_local
                fpn=nonzero(seg_true!=tile(seg0,8)[fpt])[0]; 
                sindn=self.search_downstream(sind_true[fpn],ireturn=1,msg=True)               
                sindu, fpu=unique(sindn,return_inverse=True)
                sindc,iA,iB=intersect1d(self.info.sind_bnd_local,sindu,return_indices=True)  
                if not array_equal(sindu,sindc): sys.exit('sindu!=sindc: wrong')                              
                dem=ones([8,slen])*1e5; dem.ravel()[fpt[fpn]]=self.info.dem_bnd_local[iA][fpu]
                sind=zeros([8,slen]).astype('int'); sind.ravel()[fpt[fpn]]=sind_true[fpn]
                sindc=zeros([8,slen]).astype('int'); sindc.ravel()[fpt[fpn]]=sindn
                
                iy_min=argmin(dem,axis=0);             
                sind_min=sind[iy_min,arange(slen)]; 
                dem_min=dem[iy_min,arange(slen)];
                dir_min=dir[iy_min,arange(slen)]; 
                sindc_min=sindc[iy_min,arange(slen)];         
                return sind_min,sindc_min,dem_min,dir_min                                                                    
                         
        if ireturn==10:
            seg_next=-ones(8*slen); seg_next[fpt]=self.seg.ravel()[sind_true]            
            isum=reshape(seg_next==tile(self.seg.ravel()[sind0],8),[8,slen]).sum(axis=0)
            fps=isum!=8
            return fps
        
        if ireturn==2:
            fph=nonzero(dem_true>(tile(dem0,8)[fpt]+zlimit))[0]
            num=zeros(slen*8); num[fpt[fph]]=1;             
            isum=num.reshape([8,slen]).sum(axis=0); 
            fp=isum>0; sind_next=sind0[fp]
            return sind_next
        
        #neighbor with same elevation
        fps=nonzero(abs(dem_true-tile(dem0,8)[fpt])<=zlimit)[0]
        sind_next=sind_true[fps]; 
                
        #exclude low edges
        if ireturn==4:            
            fpl=nonzero(self.dir.ravel()[sind_next]==0)[0]; fpl_len=len(sind_next)
            sind_next=sind_next[fpl]
                    
        #unique indices
        sind_next,fpu,fpu_inverse=unique(sind_next,return_index=True,return_inverse=True)
        
        if ireturn==9:
            dir_flat=zeros(slen).astype('int')        
            dem0=int(1e5)*ones(nsize).astype('int'); dem0[sind0]=dem_flat;
            dem=int(1e5)*ones([8,slen]).astype('int'); dem.ravel()[fpt[fps]]=dem0[sind_true[fps]]
            iy_min=argmin(dem,axis=0); dem_min=dem[iy_min,arange(slen)]
            dir_min=tile(array([1,64,16,4,128,32,8,2]),[slen,1]).T[iy_min,arange(slen)]           
            fp=dem_flat>dem_min; dir_flat[fp]=dir_min[fp]
            return dir_flat
        
        if ireturn==0:
            return sind_next
        
        if ireturn==1:
            num=zeros(slen*8); num[fpt[fps]]=1
            isum=reshape(num,[8,slen]).sum(axis=0).astype('int')
            return isum
        
        if ireturn in [3,4,5]:
            if wlevel==0: #first level loop
                #init
                self.sind_next=sind0.copy()
                self.sind_list=[] 
                self.flag_search=True
                self.dem_flag=zeros(nsize).astype('int32')
                                
                if ireturn in [4,5]:
                    self.v0=1
                    self.vmax=None                    
                    self.dem_flat=zeros(nsize).astype('int32') 
                    self.dem_flat_save=None
                if ireturn==4: self.sind_list.append(sind0)
                                 
                #1st round of search loop from outside to inside
                while self.flag_search:
                    sind_next=self.sind_next
                    if len(sind_next)!=0:
                        self.search_flat(sind_next,ireturn=ireturn,wlevel=1,level=0,level_max=level_max)
                        
                #2nd round of search loop from inside to outside
                if ireturn==4: 
                    self.dem_flat_save=self.dem_flat.copy()
                    for i in arange(len(self.sind_list)):
                        self.vmax=self.search_flat(self.sind_list[-i-1],ireturn=ireturn,wlevel=2,level=0,level_max=level_max)
                
                #save results
                if ireturn==3: 
                    sind=array(self.sind_list)
                else:
                    dem_flat=self.dem_flat
                    
                #clean
                delattr(self,'sind_next'); delattr(self,'sind_list');delattr(self,'dem_flag'); delattr(self,'flag_search')
                if ireturn in [4,5]: delattr(self,'v0'); delattr(self,'vmax');delattr(self,'dem_flat');delattr(self,'dem_flat_save');
                
                #return results
                if ireturn==3: 
                    return sind
                else:
                    return dem_flat

            elif wlevel==1: #2nd level search, for ireturn==3
                self.dem_flag[sind0]=1
                fpn=self.dem_flag[sind_next]==0; sind_next=sind_next[fpn]
                if ireturn==3: self.sind_list.extend(sind0);                  
                if ireturn in [4,5]: self.dem_flat[sind0]=(ones(slen)*(level+self.v0)).astype('int32')
                
                if level!=level_max:                    
                    if sum(fpn)!=0: #continue                      
                        self.search_flat(sind_next,ireturn=ireturn,wlevel=1,level=level+1,level_max=level_max)
                    else:
                        self.flag_search=False #reach the end                        
                else:                
                    if sum(fpn)!=0:
                        self.sind_next=sind_next                         
                        if ireturn in [4,5]:
                            self.sind_list.append(sind_next)
                            self.v0=int(self.v0+level_max+1)                        
                                              
            elif wlevel==2: #2nd level search, for ireturn==4 
                # self.dem_flag[sind0]=0
                vmax=self.dem_flat[sind0].copy()
                #define the sind_next using self.dem_flat_save
                fpn=nonzero(tile(vmax,8)[fpt[fps[fpu]]]<self.dem_flat_save[sind_next])[0];  
                fpn_len=len(sind_next); sind_next=sind_next[fpn]                    
                                
                if level!=level_max:                                       
                    if len(fpn)!=0: #continue                      
                        vmax_next=self.search_flat(sind_next,ireturn=ireturn,wlevel=2,level=level+1,level_max=level_max)                                                                                          
                    else:
                        self.flag_search=False #reach the end                        
                else:                
                    if sum(fpn)!=0:
                        vmax_next=self.vmax                       
                    
                #modify dem_flat
                if sum(fpn)!=0:
                    #replace vmax with vmax_next if vmax_next is larger                     
                    num_n=zeros(fpn_len); num_n[fpn]=vmax_next                                                
                    num=zeros(8*slen);  num[fpt[fps[fpl]]]=num_n[fpu_inverse] 
                    
                    nmax=reshape(num,[8,slen]).max(axis=0)                                       
                    fp=vmax<nmax; vmax[fp]=nmax[fp]
                    
                self.dem_flat[sind0]=vmax-self.dem_flat[sind0]                 
                
                return vmax
        
    def search_boundary(self,sind0,wlevel=0,level=0,level_max=100,msg=True):
        '''
        search pts of boundary pts of watershed segment, sind0 are the initial index of segments
        '''
        
        #pre-defind variables
        slen=len(sind0); ds=self.info.ds
        # print(sind0)
        iy0,ix0=unravel_index(sind0,ds)
        seg0=self.seg.ravel()[sind0]
        
        #construct matrix
        yind=r_[iy0-1,iy0-1,iy0-1,iy0,iy0+1,iy0+1,iy0+1,iy0]
        xind=r_[ix0+1,ix0,ix0-1,ix0-1,ix0-1,ix0,ix0+1,ix0+1]
        sind=-ones(8*slen).astype('int'); seg=sind.copy()
                
        #true neighbor
        fpt=nonzero((xind>=0)*(xind<ds[1])*(yind>=0)*(yind<ds[0]))[0]
        sind_true=ravel_multi_index([yind[fpt],xind[fpt]],ds); 
        fptt=self.dir.ravel()[sind_true]!=-1; fpt=fpt[fptt]; sind_true=sind_true[fptt]
        sind[fpt]=sind_true; seg[fpt]=self.seg.ravel()[sind_true]
        
        #indices belong to the same segment
        fps=seg!=tile(seg0,8); sind[fps]=-1
        
        #exclude previous cells
        # if hasattr(self,'pind'): fpn=sind==tile(self.pind,8); sind[fpn]=0
        if hasattr(self,'ppind'): fpn=sind==tile(self.ppind,8); sind[fpn]=-1
        
        sind=sind.reshape([8,slen])
        
        iy0=zeros(slen).astype('int'); 
        if hasattr(self,'pind'):
            pind=self.pind
        else:
            pind=0
        #find the starting search pt
        for i in arange(8):
            fp=sind[i,:]==pind
            iy0[fp]=i
        
        #find the next pts
        sind_next=-ones(slen).astype('int')
        ix=arange(slen).astype('int')
        for i in arange(8):
            iy0=iy0+1
            iy1=mod(iy0,8); iy2=mod(iy0+1,8)
            fpn=(sind[iy1,ix]==-1)*(sind[iy2,ix]!=-1)*(sind_next==-1)
            sind_next[fpn]=sind[iy2,ix][fpn]
        
        #if sind_next=0, search back
        fpb=sind_next==-1; sind_next[fpb]=sind0[fpb]      
              
        #recursive search 
        if wlevel==0:
            #init
            self.sind_next=sind0.copy()
            self.sind0=sind0.copy()
            self.pind=sind0.copy() #previous pts
            self.ppind=sind0.copy() #previous pts
            self.flag_search=True
            self.sind_list=[[i] for i in sind0]
            self.snum=arange(slen).astype('int')
            
            #1-level search loop
            iflag=0
            while self.flag_search:                
                iflag=iflag+1;
                if msg: print('search boundary: loop={}, npt={}'.format(iflag,len(self.sind_next)))
                if len(self.sind_next)==0: break
                self.search_boundary(self.sind_next,wlevel=1,level=0,level_max=level_max)
                #print('search bnd: {}'.format(iflag*level_max))
                
            #save list info
            sind_list=array([array(i) for i in self.sind_list])
            
            #clean
            delattr(self,'sind_next'); delattr(self,'sind0'); delattr(self,'flag_search')
            delattr(self,'sind_list'); delattr(self,'snum'); delattr(self,'pind');delattr(self,'ppind');
            
            return sind_list
            
        elif wlevel==1:
            fpz=sind_next!=self.sind0
            [self.sind_list[i].append(j) for i,j in zip(self.snum[~fpz],sind_next[~fpz])]
            if sum(fpz)==0: self.flag_search=False
            if (level!=level_max) and sum(fpz)!=0: #not reach the end                                
                self.sind0=self.sind0[fpz]
                self.snum=self.snum[fpz]
                self.ppind=self.pind[fpz]
                self.pind=self.sind_next[fpz]
                self.sind_next=sind_next[fpz]
                
                #save pts to the list    
                [self.sind_list[i].append(j) for i,j in zip(self.snum,self.sind_next)]
                
                #continue search
                self.search_boundary(self.sind_next,wlevel=1,level=level+1,level_max=level_max)
                                     
    def search_upstream(self,sind0,ireturn=0,seg=None,acc_limit=0,wlevel=0,level=0,level_max=100,acc_calc=False,msg=True):
        '''
        ireturn=0: all the 1-level upstream index. if seg is not None, return seg number (seg_up) also
        ireturn=1: all the 1-level upstream index, also with flags of true neighbor and incoming flow
        ireturn=2: number of upstream indices 
        ireturn=3: search all upstreams, compute acc and seg
        ireturn=4: just one-level upstream index with largest acc 
        ireturn=5: all the one-level upstream index except the one with largest acc, and numbering index
        ireturn=6: uppermost upstream index along the largest river stem
        ireturn=7: save all the cells along the largest upstream river
        ireturn=8: return how many neighbors with same segment number after acc and seg are known
        ireturn=9: return segment boundary indices
        '''
             
        #--pre-define variables        
        slen=len(sind0); ds=self.info.ds
        dir_in0=[8,4,2,1,128,64,32,16]
        
        #convert index
        iy0,ix0=unravel_index(sind0,ds)
                       
        #compute init neighbor index
        yind=r_[iy0-1,iy0-1,iy0-1,iy0,iy0+1,iy0+1,iy0+1,iy0]
        xind=r_[ix0+1,ix0,ix0-1,ix0-1,ix0-1,ix0,ix0+1,ix0+1]
        if seg is not None: seg0=tile(seg,8)
        
        #true neighbor index
        fpt=nonzero(((xind>=0)*(xind<ds[1])*(yind>=0)*(yind<ds[0])).ravel())[0]
        
        #init dir
        dir_in=tile(dir_in0,[len(sind0),1]).T.ravel()
        
        #true neighbor
        sind_true=ravel_multi_index([yind[fpt],xind[fpt]],ds);
        fptt=self.dir.ravel()[sind_true]!=-1; fpt=fpt[fptt]; sind_true=sind_true[fptt]
        if seg is not None: seg_true=seg0[fpt]
        
        #dir diff for true neighbors  
        dir_diff=self.dir.ravel()[sind_true]-dir_in[fpt]
        
        #index of neighbors with incoming flow
        fpf=nonzero(dir_diff==0)[0]
        sind_up=sind_true[fpf] 
        if seg is not None: seg_up=seg_true[fpf]
        
        if ireturn==0: 
            if seg is None:
                return sind_up
            else:
                return sind_up, seg_up
        
        if ireturn==1:
            return sind_up, fpt[fpf]
        
        if ireturn==2:
            num=zeros(slen*8); num[fpt[fpf]]=1
            num_up=(reshape(num,[8,slen]).sum(axis=0)).astype('int')
            return num_up
        
        if ireturn==8:
            seg0=self.seg.ravel()[sind0]
            #method 1
            fps=nonzero(tile(seg0,8)[fpt]==self.seg.ravel()[sind_true])[0]
            num=zeros(slen*8); num[fpt[fps]]=1
            
            num_up=(reshape(num,[8,slen]).sum(axis=0)).astype('int')
            return num_up
        
        if ireturn==3:
            if wlevel==0: #first level recursive search 
                #init
                if seg is None: 
                    seg0=arange(slen)+1
                    self.acc=zeros(prod(ds)).astype('int'); self.acc[self.dir.ravel()==-1]=-1                                                 
                else:
                    seg0=seg
                    
                self.seg=zeros(prod(ds)).astype('int'); self.seg[self.dir.ravel()==-1]=-1
                self.sind_list=[]; 
                self.seg_list=[];
                self.flag_search=True
                                    
                self.sind_next=sind0.copy(); self.seg_next=seg0; 
                self.sind_list.append(sind0); self.seg_list.append(seg0) 
                      
                #1-level search loop, from downstream to upstream
                iflag=0
                while self.flag_search:
                    iflag=iflag+1
                    if msg: print('search upstream,ireturn={}: loop={}, npt={}'.format(ireturn,iflag,len(self.sind_next)))
                    if len(self.sind_next)==0: break
                    self.search_upstream(self.sind_next,ireturn=ireturn,seg=self.seg_next, wlevel=1,level=0,level_max=level_max)
                
                #search from upstream to downstream on the 1-level
                for i in arange(len(self.sind_list)):   
                    if seg is not None: continue                    
                    if msg: print('search upstream backward,ireturn={}: loop={}, npt={}'.format(ireturn,len(self.sind_list)-i,len(self.sind_list[-i-1])))
                    self.search_upstream(self.sind_list[-i-1],ireturn=ireturn,seg=self.seg_list[-i-1], wlevel=1,level=0,level_max=level_max,acc_calc=True)
                
                #clean 
                delattr(self,'sind_list');delattr(self,'seg_list'); delattr(self,'flag_search')
                delattr(self,'sind_next'); delattr(self,'seg_next')
                if seg is None: delattr(self,'seg')
                    
                #reshape
                if hasattr(self,'acc'): self.acc=self.acc.reshape(ds)                
                if seg is not None: self.seg=self.seg.reshape(ds)
                
                return
                         
            elif wlevel==1: #2-level recursive search    
                #assign seg number
                self.seg[sind0]=seg            
               
                acc_up=0; acc=0
                if level!=level_max:    
                    if len(sind_up)==0: #reach the end
                        self.flag_search=False                        
                    else:                                             
                        acc_up=self.search_upstream(sind_up,ireturn=ireturn,seg=seg_up,wlevel=1,level=level+1,level_max=level_max,acc_calc=acc_calc) 
                                         
                else:
                    if not acc_calc:
                        self.sind_next=sind_up
                        self.seg_next=seg_up
                        self.sind_list.append(sind_up)                    
                        self.seg_list.append(seg_up)
                    else:
                        acc_up=self.acc[sind_up]  
                
                if acc_calc:
                    #compute acc for sind0
                    #get flags of sind_up first      
                    sind_up,fptf=self.search_upstream(sind0,ireturn=1)
                    acc0=zeros(slen*8); acc0[fptf]=acc_up                     
                    acc=reshape(acc0,[8,slen]).sum(axis=0)+1
                    
                    self.acc[sind0]=acc
                
                return acc   
        
        #----------------------------------------------------------------------
        #code below works after self.acc is computed, except for ireturn=9
        #----------------------------------------------------------------------
        sind=-ones(8*slen).astype('int'); sind[fpt[fpf]]=sind_up
        
        if ireturn==9:                                                            
            sind_next=sind_up           
        else:
            #get corresponding acc
            acc=zeros(slen*8).astype('int'); acc[fpt[fpf]]=self.acc.ravel()[sind_up];            
            acc=acc.reshape([8,slen]); sind=sind.reshape([8,slen]) 
            
            #apply limit
            if acc_limit!=0:
                fpc=acc<acc_limit; acc[fpc]=0; sind[fpc]=-1;
                
            #get index for cells_next with maximum acc
            ix=arange(slen).astype('int'); iy=argmax(acc,axis=0)        
            sind_next=sind[iy,ix]
           
        #just one level
        if ireturn==4:
            return sind_next
        
        #one-level upstream, all the cells except the largest one
        if ireturn==5:            
            sind[iy,ix]=-1; fpn=sind!=-1;
            nind0=tile(arange(slen),8).reshape([8,slen]).astype('int') 
            sind_next=sind[fpn]; nind=nind0[fpn]
            return sind_next,nind
        
        #get to the uppermost pts, using 2-level recursive search. 
        #1-level recursive search will crash reaching the setrecursionlimit
        if ireturn in [6,7,9]:            
            if wlevel==0: #first level recursive
                #init
                #if not hasattr(self,'sind_next'):
                self.sind_next=sind0.copy()
                self.sind_flag=ones(slen)
                self.flag_search=True
                self.sind_list=[[i] for i in sind0]
                self.sind_bnd=[[] for i in sind0]
                self.sind_seg=[[] for i in sind0]
                self.seg_next=arange(slen)                                   
                
                #1-level search loop
                iflag=0
                while self.flag_search:
                    iflag=iflag+1
                    if msg: print('search upstream,ireturn={}: loop={}, npt={}'.format(ireturn,iflag,len(self.sind_next)))
                    if ireturn==9:
                        sind_next=self.sind_next
                    else:
                        fp=self.sind_flag>0; sind_next=self.sind_next[fp]                        
                    if len(sind_next)==0: break;                    
                    self.search_upstream(sind_next,ireturn=ireturn,seg=self.seg_next,acc_limit=acc_limit,wlevel=1,level=0,level_max=level_max,acc_calc=acc_calc) 
                
                #search finished at this point
                sind_next=self.sind_next                
                sind_list=array([array(i) for i in self.sind_list]) 
                sind_bnd=array([array(i) for i in self.sind_bnd]) 
                sind_seg=array([sort(array(i)).astype('int') for i in self.sind_seg]) 
                
                #clean
                delattr(self,'sind_next'); delattr(self,'flag_search'); delattr(self,'sind_list')
                delattr(self,'sind_bnd'); delattr(self,'seg_next'); delattr(self,'sind_flag'); delattr(self,'sind_seg')
                
                if ireturn==6:
                    return sind_next
                elif ireturn==7:
                    return sind_list
                elif ireturn==9:
                    if acc_calc:
                        return sind_seg
                    else:
                        return sind_bnd
                                     
            elif wlevel==1: #second level recursive search                 
                fpnz=nonzero(sind_next!=-1)[0]; fpz=nonzero(sind_next==-1)[0]
                if level!=level_max:
                    if ireturn==9:
                        seg_next=seg_up
                        #collect boundary cells                              
                        isum=sind.reshape([8,slen]).sum(axis=0); fpb=isum==-8
                        [self.sind_bnd[i].append(j) for i,j in zip(seg[fpb],sind0[fpb])]
                        if acc_calc:
                            [self.sind_seg[i].append(j) for i,j in zip(seg,sind0)]
                    else:
                        seg_next=self.seg_next
                        
                    if len(fpnz)==0:
                        #reach the end
                        if ireturn!=9: fpn=self.sind_flag>0; self.sind_next[fpn]=sind0
                        if ireturn==7:
                            ind_list=nonzero(fpn)[0]; sind_list=sind0
                            [self.sind_list[i].append(j) for i,j in zip(ind_list,sind_list)]
                        self.flag_search=False
                    else:
                        if ireturn==9:
                            self.sind_next=sind_up
                            self.seg_next=seg_next
                        else:
                            #save the pts that reach the end
                            sind_next[fpz]=sind0[fpz]
                            fpn=self.sind_flag>0; self.sind_next[fpn]=sind_next; self.sind_flag[nonzero(fpn)[0][fpz]]=0
                        if ireturn==7:
                            ind_list=nonzero(fpn)[0]; sind_list=abs(sind_next)
                            [self.sind_list[i].append(j) for i,j in zip(ind_list,sind_list)]
                        
                        #continue search the rest pts 
                        self.search_upstream(sind_next[fpnz],ireturn=ireturn,seg=seg_next,acc_limit=acc_limit,wlevel=1,level=level+1,level_max=level_max,acc_calc=acc_calc)
                        
    def search_downstream(self,sind0,ireturn=0,wlevel=0,level=0,level_max=500,msg=True):
        '''
        ireturn=0: return 1-level downstream index
        ireturn=1: most downstream index
        ireturn=2: save all the index along the downstream, return if reach dir=0. 
                   return downstream network. This will fail for loops
        ireturn=3: save all the index along the downstream, return if reach dir=0 or identify loops
                   return downstream network and flag for loops (0: not loop; 1: 1st-type loop; 2: 2nd-type loop). 
        ireturn=4: save length from upstream to downstream
        '''
        
        #pre-define variables
        slen=len(sind0); ds=self.info.ds
        
        #variables for each direction
        dir_out=array([128,64,32,16,8,4,2,1]).astype('int')
        offset_y=array([-1,-1,-1,0,1,1,1,0]).astype('int')
        offset_x=array([1,0,-1,-1,-1,0,1,1]).astype('int')
        
        #check each dir
        sdir=self.dir.ravel()[sind0]
        iy0,ix0=unravel_index(sind0,ds)       
        yind=-ones(slen).astype('int'); xind=yind.copy(); sind_next=yind.copy()
        for i in arange(8):
            fp=sdir==dir_out[i]
            yind[fp]=iy0[fp]+offset_y[i]
            xind[fp]=ix0[fp]+offset_x[i]
        
        #true donwstream
        fpt=(xind>=0)*(xind<ds[1])*(yind>=0)*(yind<ds[0])
        if sum(fpt)!=0:
            sind_next[fpt]=ravel_multi_index([yind[fpt],xind[fpt]],ds)
            
        if ireturn==0:
            return sind_next
        
        if ireturn in [1,2,3,4]:
            if wlevel==0: #first level recrusive search
                #init
                #if not hasattr(self,'sind_next'):
                self.sind_next=sind0.copy()
                self.flag_search=True
                self.flag_next=ones(slen)==1
                self.sind_list=[[i] for i in sind0]
                self.len_stream=zeros(slen).astype('int')
                
                #1-level search loop
                iflag=0
                while self.flag_search:
                     iflag=iflag+1;
                     if msg: print('search downstream,ireturn={}: loop={}, npt={}'.format(ireturn,iflag,sum(self.flag_next)))
                     
                     #to check whether there is a loop
                     if ireturn==3:
                         ns0=array([len(i) for i in self.sind_list])
                         ns=array([len(unique(i)) for i in self.sind_list])
                         fpe=nonzero(((ns0-ns)>1)*(self.flag_next))[0]
                         for i in arange(len(fpe)):
                              self.sind_list[fpe[i]]=self.sind_list[fpe[i]][:ns[fpe[i]]+2]                            
                         self.flag_next[fpe]=False
                                          
                     if sum(self.flag_next)==0: break;                    
                     self.search_downstream(self.sind_next[self.flag_next],ireturn=ireturn,wlevel=1,level=0,level_max=level_max) 
                      
                #search finished at this point
                sind_next=self.sind_next
                if ireturn==2:                
                    sind_list=array([array(i)[:-1] for i in self.sind_list])                
                elif ireturn==3:
                    sind_list=array([array(i)[:-1] for i in self.sind_list])                    
                    ns0=array([len(i) for i in sind_list])
                    ns=array([len(unique(i)) for i in sind_list])
                    fpl=array([i[0]==i[-1] for i in sind_list])*(ns0!=1)
                    
                    flag_loop=zeros(slen).astype('int')
                    flag_loop[ns0!=ns]=2; flag_loop[fpl]=1                    
                elif ireturn==4:
                    len_stream=self.len_stream.copy()
                
                #clean
                delattr(self,'sind_next'); delattr(self,'flag_search'); delattr(self,'flag_next') 
                delattr(self,'sind_list'); delattr(self,'len_stream'); 
                
                if ireturn==1:
                    return sind_next
                elif ireturn==2:            
                    return sind_list  
                elif ireturn==3:
                    return sind_list, flag_loop
                elif ireturn==4:
                    return len_stream
                
            elif wlevel==1: #second level recursive search
                fpz=nonzero(self.flag_next)[0]     
                fpn=nonzero(sind_next==-1)[0]
                fpp=nonzero(sind_next!=-1)[0]
                   
                if level!=level_max:
                    if len(fpp)==0:
                        #reach the end
                        self.sind_next[fpz]=sind0
                        if ireturn in [2,3]:                           
                            [self.sind_list[i].append(j) for i,j in zip(fpz,sind0)]
                        elif ireturn==4:                            
                            self.len_stream[fpz]=self.len_stream[fpz]+1
                            
                        self.flag_search=False
                    else:
                        #save the pts that reach the end
                        sind_next[fpn]=sind0[fpn]
                        self.sind_next[fpz]=sind_next  
                        self.flag_next[fpz[fpn]]=False
                        if ireturn in [2,3]:
                            [self.sind_list[i].append(j) for i,j in zip(fpz,sind_next)]
                        elif ireturn==4:                            
                            self.len_stream[fpz]=self.len_stream[fpz]+1
                        
                        #continue search the rest pts 
                        self.search_downstream(sind_next[fpp],ireturn=ireturn,wlevel=1,level=level+1,level_max=level_max)                              
            
    # def compute_extent(self,header=None):
    #     #recalculate extent from header
    #     if header is None: header=self.info.header
    #     ym,xm,yll,xll,dxy=header        
    #     extent=array([xll,xll+(xm-1)*dxy,yll,yll+(ym-1)*dxy])
    #     return extent
        
    def remove_nan(self,name='dem',nodata=-99999):
        '''
        change nan to nodata                
        '''
        
        fpn=isnan(self.dem)|(self.dem==self.info.nodata)
        self.dem[fpn]=nodata
        self.info.nodata=nodata
    
    def get_coordinates(self,sind0,header=None,nodata=None):
        '''
        example: sind0=nonzero(self.dir.ravel()==0)[0], or sind0=nonzero(self.dir==0)
        '''
        
        #check parameters first
        if header is None: header=self.info.header
        if nodata is None: nodata=self.info.nodata
        ym,xm,yll,xll,dxy=header; ds=[ym,xm]
        
        sind=sind0.copy().ravel(); 
        #check index
        if len(sind)==2 and hasattr(sind[0],'__len__'):            
            indy,indx=sind  #sind0=[indy,indx]            
            fpn=(indy==nodata)|(indx==nodata)
        else:
            fpn=sind0==nodata; sind[fpn]=0;
            indy,indx=unravel_index(sind,ds)
            indy[fpn]=nodata; indx[fpn]=nodata
            
        #convert index to coordinates            
        xi=xll+indx*dxy; xi[fpn]=nodata
        yi=yll-indy*dxy; yi[fpn]=nodata
        
        #reshape
        xi=reshape(xi,sind0.shape)
        yi=reshape(yi,sind0.shape)        
        
        return yi,xi
    
    def write_shapefile(self,data,sname,stype='POLYLINE',prjname='epsg:4326',attname=None,attvalue=None):
        '''
        data: string name or data
        sname: shapefile name
        '''
        
        #get data
        S=npz_data()
        if type(data)==type(''):
            exec('S.data=self.{}'.format(data))
        else:
            S.data=data
        
        #get type and prj
        S.type=stype
        S.prj=get_prj_file(prjname)
        
        #get attrs
        if (attname is not None) and (attvalue is not None):
            S.attname=attname
            S.attvalue=attvalue
        
        #get xy
        S.xy=[];
        for i in arange(len(S.data)):            
            yi,xi=self.get_coordinates(S.data[i])
            fp=(xi==self.info.nodata)|(yi==self.info.nodata);
            xi[fp]=nan; yi[fp]=nan;            
            S.xy.append(c_[xi,yi])
        S.xy=array(S.xy)
        
        #write shapefile
        write_shapefile_data(sname,S)
                 
if __name__=="__main__":    
    close('all')
    
# # #------------------------------------------------------------------------------    
#     #init
#     S=dem(); S.read_data('S9_m.npz')
#     ds=S.info.ds; ym,xm=ds; level_max=100; 
    
    
#     #this part assign dir directly if the original dir of boundary cells is not zero
#     sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds); 
#     fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); sind0=sind0[fp]
#     dem0=S.info.dem_bnd_local[fp]; dir0=S.info.dir_bnd_local[fp]; #original
#     dir=S.dir.ravel()[sind0] #at present
    
#     #exclude nodata bnd pts
#     if len(S.info.sind_bnd_nodata)!=0:
#         sind_bnd_nodata,iA,iB=intersect1d(sind0,S.info.sind_bnd_nodata,return_indices=True)
#         fp=setdiff1d(arange(len(sind0)),iA)
#         sind0=sind0[fp]; dem0=dem0[fp]; dir0=dir0[fp]; dir=dir[fp]
    
#     print('---------assign dir directly if original dir is not zero------')
#     #put flow into another seg if its original dir is not zero, it doesn't form loops    
#     fpz=nonzero((dir0!=0)*(dir==0))[0]; 
#     S.dir.ravel()[sind0[fpz]]=dir0[fpz]
    
#     #excude pts that forms loops          
#     sind_list,flag_loop=S.search_downstream(sind0[fpz],ireturn=3,msg=True); 
#     fpl=nonzero(flag_loop==1)[0]; sindl=sind0[fpz[fpl]]; deml=dem0[fpz[fpl]] 
#     sind_list=array([intersect1d(sindl,i) for i in sind_list[fpl]])   
#     sind_all=[]; ids=[]; id1=0; id2=0;  
#     for i in arange(len(fpl)):            
#         sindi=unique(sind_list[i]); id2=id1+len(sindi)
#         sind_all.extend(sindi)        
#         ids.append(arange(id1,id2).astype('int')); id1=id1+len(sindi) 
#     sind_all=array(sind_all)
#     sindu,fpu=unique(sind_all,return_inverse=True); sindc,iA,iB=intersect1d(sindu,sindl,return_indices=True)
#     if not array_equal(sindu,sindc): sys.exit('sindc!=sindu') 
#     dem_all=deml[iB][fpu]
#     sind_min=unique(array([sind_all[id[nonzero(dem_all[id]==min(dem_all[id]))[0]]] for id in ids]))
#     S.dir.ravel()[sind_min]=0
    
#     S.fill_depression(method=1)
    
#     S.compute_watershed()
#     S.compute_river(arange(1,1e5),acc_limit=1e3)
#     S.write_shapefile('rivers','B1_1_rivers')
#     sys.exit()
    
#     print('---------assign dir to neighboring segs if possible-----------')
#     #this loop part assigns dir to neighboring segs of dir=0
#     iflag=0
#     while True:      
#         iflag=iflag+1
#         #identify depression catchment
#         sind0=self.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
#         fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(self.dir.ravel()[sind0]==0); 
#         sind0=sind0[fp]; h0=self.info.dem_bnd_local[fp]
        
#         #exclude nodata bnd pts
#         if len(self.info.sind_bnd_nodata)!=0:
#             sind_bnd_nodata,iA,iB=intersect1d(sind0,self.info.sind_bnd_nodata,return_indices=True)
#             fp=setdiff1d(arange(len(sind0)),iA)
#             sind0=sind0[fp]; h0=h0[fp]; 
                                                         
#         #search and mark each depression            
#         slen=len(sind0); seg0=arange(slen)+1
#         self.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max,msg=False)
#         print('fill depression: loop={}, ndep={}'.format(iflag,slen))
        
#         #find all the neighboring indices with minimum depth seg 
#         sind_min,sind0_min,h0_min, dir_min=self.search_flat(sind0,ireturn=8,method=1)        
#         if sum(sind_min!=0)==0: break        
#         #reverse dir first
#         dir_min0=dir_min.copy(); dir_min[:]=0
#         dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
#         for i in arange(8):
#             fpr=dir_min0==dir_0[i]; dir_min[fpr]=dir_inv[i] 
            
#         #assign dir to the nearest seg with minimum depth; if h0=h0_min, use smaller sind0     
#         fpm=nonzero(((h0>h0_min)*(sind_min!=0))|((h0==h0_min)*(sind_min!=0)*(sind0<sind0_min)))[0]
#         if len(fpm)==0: fpm=nonzero((h0==h0_min)*(sind_min!=0)*(sind0>sind0_min))[0]
#         if len(fpm)==0: break
#         self.dir.ravel()[sind0[fpm]]=dir_min[fpm]
#         sind_list,flag_loop=self.search_downstream(sind0[fpm],ireturn=3)
#         if sum(flag_loop!=0)!=0: sys.exit('loop found: impossible') 
    
        
# #     #--------------------------------------------------------------------------
#         S.fill_depression(method=1);
    
#         S.compute_watershed()
#         S.compute_river(arange(1,1e5),acc_limit=1e3)
#         S.write_shapefile('rivers','A1_5_rivers')
#         sys.exit()

#------------------------------------------------------------------------------
#******************************************************************************
#------------------------------------------------------------------------------
    
#     #------fill depression ----------------------------------------------------
#         #pre-define variables       
#     ds=S.info.ds; ym,xm=ds
            
#     #initialize
#     sind0=nonzero(S.dir.ravel()==0)[0]; 
    
#     #exclude boundary pts
#     iy,ix=unravel_index(sind0,ds)
#     fp=(ix>0)*(ix<(xm-1))*(iy>0)*(iy<(ym-1)); sind0=sind0[fp]
#     # if sind0.size==0: return        
    
#     #resolve flats         
#     print('---------resolve DEM flats------------------------------------')
#     isum=S.search_upstream(sind0,ireturn=2)
#     S.resolve_flat(sind0[isum==0])    

          
#     #identify depression catchment
#     sind0=nonzero(S.dir.ravel()==0)[0]; iy,ix=unravel_index(sind0,ds)
#     fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); sind0=sind0[fp]
    
#     #search and mark each depression
#     print('---------identify and mark depressions------------------------')
#     slen=len(sind0); seg0=arange(slen)+1; h0=S.dem.ravel()[sind0];  
#     S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max)
    
#     #get indices for each depression; here seg is numbering, not segment number
#     print('---------save all depression points---------------------------')
#     sind_segs=S.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=level_max)
#     ns0=array([len(i) for i in sind_segs])                  
  
#     #get depression boundary
#     print('---------compute depression boundary--------------------------')
#     S.compute_boundary(sind=sind0); 
    

#     sind_linkx,flag_loopx=S.search_downstream(sindxx,ireturn=3)
    
#     sys.exit()
    
#     #loop to reverse dir along streams
#     print('---------fill depressions-------------------------------------')
#     ids=arange(slen); iflag=0
#     while len(sind0)!=0:
#         iflag=iflag+1
#         print('fill depression: loop={}, ndep={}'.format(iflag,slen))
#         # slen=len(ids); h0=h00[ids]; sind0=sind00[ids]; ns0=ns00[ids]
#         # ids=arange(slen)
#         #-------------------------------------------------------------------------
#         #seg0,     ns0,     h0,      sind0,       sind_bnd,   h_bnd
#         #seg_min,  ns_min,  h0_min,  sind0_min,   sind_min,   h_min  h_bnd_min  dir_min
#         #-------------------------------------------------------------------------        
        
#         #exclude nonboundary indices
#         sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
#         for i in arange(slen):            
#             sindi=unique(self.boundary[i]); id2=id1+len(sindi)
#             sind_bnd_all.extend(sindi)        
#             ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)                         
#         sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd)
#         flag_bnd_all=self.search_flat(sind_bnd_all,ireturn=10)
#         for i in arange(slen):
#             self.boundary[i]=sind_bnd_all[ids_bnd[i][flag_bnd_all[ids_bnd[i]]]]
            
#         #recalcuate bnd for seg with false boundary
#         len_seg=array([len(i) for i in sind_segs]); 
#         len_bnd=array([len(i) for i in self.boundary])
#         idz=nonzero((len_bnd==0)*(len_seg!=0))[0]
#         if len(idz)!=0:
#             #save boundary first
#             boundary=self.boundary.copy(); delattr(self,'boundary')
#             self.compute_boundary(sind=sind0[idz]);
#             if len(idz)==1:
#                 boundary[idz[0]]=self.boundary[0]
#             else:
#                 boundary[idz]=self.boundary
                
#             self.boundary=boundary; boundary=None
                                    
#         #rearange the boundary index
#         sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
#         for i in arange(slen):            
#             sindi=self.boundary[i]; id2=id1+len(sindi)
#             sind_bnd_all.extend(sindi)        
#             ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)             
#         sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd);
        
#         #find all the neighboring indices with minimum depth
#         sind_min_all,h_min_all,dir_min_all=self.search_flat(sind_bnd_all,ireturn=8)
                
#         #minimum for each seg
#         h_min=array([h_min_all[id].min() for id in ids_bnd])
#         mind=array([nonzero(h_min_all[id]==hi)[0][0] for id,hi in zip(ids_bnd,h_min)])        
#         sind_bnd=array([sind_bnd_all[id][mi] for id,mi in zip(ids_bnd,mind)]); h_bnd=self.dem.ravel()[sind_bnd]
#         sind_min=array([sind_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
#         dir_min=array([dir_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
        
#         #get s0_min,h0_min,sind0_min
#         seg_min=self.seg.ravel()[sind_min]; fps=nonzero(seg_min!=0)[0]; 
                
#         ind_sort=argsort(seg_min[fps]);  
#         seg_1, ind_unique=unique(seg_min[fps[ind_sort]],return_inverse=True)
#         seg_2,iA,iB=intersect1d(seg_1,seg0,return_indices=True)        
#         ids_min=zeros(slen).astype('int'); ids_min[fps[ind_sort]]=ids[iB][ind_unique]
        
#         ns_min=zeros(slen).astype('int');    ns_min[fps]=ns0[ids_min[fps]]
#         h0_min=-1e5*ones(slen);              h0_min[fps]=h0[ids_min[fps]]
#         sind0_min=-ones(slen).astype('int'); sind0_min[fps]=sind0[ids_min[fps]]
#         h_bnd_min=zeros(slen);               h_bnd_min[fps]=h_bnd[ids_min[fps]]
    
#         #get stream from head to catchment
#         fp1=seg_min==0; 
#         fp2=(seg_min!=0)*(h0_min<h0); 
#         fp3=(seg_min!=0)*(h0_min==h0)*(ns_min>ns0)
#         fp4=(seg_min!=0)*(h0_min==h0)*(ns_min==ns0)*(h_bnd>h_bnd_min); 
#         fp5=(seg_min!=0)*(h0_min==h0)*(ns_min==ns0)*(h_bnd==h_bnd_min)*(sind0>sind0_min);         
#         fph=nonzero(fp1|fp2|fp3|fp4|fp5)[0]; sind_head=sind_bnd[fph];
#         # if len(fph)==0: 
#         #     #sind0 is on the boundary bounded by nodata
#         #     self.info.sind_bnd=r_[self.info.sind_bnd,sind0]
#         #     if hasattr(self.info,'dir_bnd'): self.info.dir_bnd=r_[self.info.dir_bnd,self.dir.ravel()[sind0]]
#         #     if hasattr(self.info,'dem_bnd'): self.info.dem_bnd=r_[self.info.dem_bnd,self.dem.ravel()[sind0]]  
#         #     if self.info.is_subdomain:
#         #         biy,bix=unravel_index(sind0,ds); biy=biy+self.info.bxy_global[0]; bix=bix+self.info.bxy_global[1]; 
#         #         self.info.sind_bnd_global=r_[self.info.sind_bnd_global, ravel_multi_index([biy,bix],self.info.ds_global)]
#         #     break            
#         sind_streams=self.search_downstream(sind_head,ireturn=2,msg=False)        
                
#         #get all stream index and its dir
#         sind=[]; dir=[];
#         for i in arange(len(fph)):
#             id=fph[i];    
#             #S.seg.ravel()[sind_segs[id]]=seg_min[id]; seg0[id]=seg_min[id]
#             sind_stream=sind_streams[i]
#             dir_stream=r_[dir_min[id],self.dir.ravel()[sind_stream][:-1]]            
#             sind.extend(sind_stream); dir.extend(dir_stream)
#             if len(sind)!=len(dir):
#                 x=5
#         sind=array(sind); dir0=array(dir).copy(); dir=zeros(len(dir0)).astype('int')
            
#         #reverse dir
#         dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
#         for i in arange(8):
#             fpr=dir0==dir_0[i]; dir[fpr]=dir_inv[i]    
#         self.dir.ravel()[sind]=dir;
        
#         #----build the linkage--------------------------------------------------
#         s_0=seg0.copy(); d_0=seg_min.copy(); d_0[setdiff1d(arange(slen),fph)]=-1
#         while True:         
#             fpz=nonzero((d_0!=0)*(d_0!=-1))[0] 
#             if len(fpz)==0: break         
        
#             #assign new value of d_0
#             s1=d_0[fpz].copy(); 
                        
#             ind_sort=argsort(s1); 
#             s2,ind_unique=unique(s1[ind_sort],return_inverse=True)
#             s3,iA,iB=intersect1d(s2,s_0,return_indices=True)            
#             d_0[fpz[ind_sort]]=d_0[iB[ind_unique]]
            
#             #assign new value fo s_0
#             s_0[fpz]=s1;
        
#         #--------------------------
#         seg_stream=seg0[fph[d_0[fph]==-1]] #seg that flows to another seg (!=0)        
#         seg_tmp,iA,sid=intersect1d(seg_stream,seg0,return_indices=True)
        
#         seg_target=s_0[fph[d_0[fph]==-1]]; tid=zeros(len(seg_target)).astype('int'); 
#         ind_sort=argsort(seg_target); seg_tmp, ind_unique=unique(seg_target[ind_sort],return_inverse=True)
#         seg_tmp,iA,iB=intersect1d(seg_target,seg0,return_indices=True);
#         tid[ind_sort]=iB[ind_unique]
#         #----------------------------------------------------------------------
                    
#         #reset variables-----
#         ids_stream=ids[fph]; ids_left=setdiff1d(ids,ids_stream)        

#         #collect boundary        
#         for si,ti in zip(sid,tid):                        
#             self.seg.ravel()[sind_segs[si]]=seg0[ti]
#             self.boundary[ti]=r_[self.boundary[ti],self.boundary[si]]
#             sind_segs[ti]=r_[sind_segs[ti],sind_segs[si]]
#             ns0[ti]=ns0[ti]+ns0[si]
               
#         #set other seg number to zeros
#         seg_stream2=seg0[fph[d_0[fph]==0]] #seg that flows to another seg (!=0)        
#         seg_tmp,iA,sid2=intersect1d(seg_stream2,seg0,return_indices=True)
#         for si in sid2:
#             self.seg.ravel()[sind_segs[si]]=0
        
#         #update variables    
#         sind0=sind0[ids_left]; seg0=seg0[ids_left]; h0=h0[ids_left]; ns0=ns0[ids_left]
#         self.boundary=self.boundary[ids_left]; sind_segs=sind_segs[ids_left]
#         slen=len(sind0); ids=arange(slen)
#     #clean
#     delattr(self,'seg');delattr(self,'boundary')


#     #----------------------------
#     S.compute_watershed()
#     S.compute_river(arange(1,1e5),acc_limit=1e3)
    
#     dirx=S.dir.ravel()[sindx]   
#     S.write_shapefile('rivers','A1_5_rivers')
#     sys.exit()
#     #-----------------------this part assign dir to neighboring segs of dir=0--
#     while True:      
#         #identify depression catchment
#         sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
#         fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(S.dir.ravel()[sind0]==0); 
#         sind0=sind0[fp]; h0=S.info.dem_bnd_local[fp]
                                    
#         #search and mark each depression
#         print('---------identify and mark depressions------------------------')
#         slen=len(sind0); seg0=arange(slen)+1
#         S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max,msg=True)
        
#         #find all the neighboring indices with minimum depth seg 
#         sind_min,sind0_min,h0_min, dir_min=S.search_flat(sind0,ireturn=8,method=1)        
#         if sum(sind_min!=0)==0: break        
#         #reverse dir first
#         dir_min0=dir_min.copy(); dir_min[:]=0
#         dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
#         for i in arange(8):
#             fpr=dir_min0==dir_0[i]; dir_min[fpr]=dir_inv[i] 
            
#         #assign dir to the nearest seg with minimum depth; if h0=h0_min, use smaller sind0     
#         fpm=nonzero(((h0>h0_min)*(sind_min!=0))|((h0==h0_min)*(sind_min!=0)*(sind0<sind0_min)))[0]
#         if len(fpm)==0: fpm=nonzero((h0==h0_min)*(sind_min!=0)*(sind0>sind0_min))[0]
#         if len(fpm)==0: break
#         S.dir.ravel()[sind0[fpm]]=dir_min[fpm]
#         sind_list,flag_loop=S.search_downstream(sind0[fpm],ireturn=3)
#         if sum(flag_loop!=0)!=0: sys.exit('loop found: impossible')  
    
    

#------------------------------------------------------------------------------
    # S=dem(); S.read_data('S8_m.npz');
    # ds=S.info.ds; ym,xm=ds; level_max=100
    
    
    # S.fill_depression()
    # sys.exit()
    # #exclude boundary pts
    # sind0=nonzero(S.dir.ravel()==0)[0]; 
    # iy,ix=unravel_index(sind0,ds)
    # fp=(ix>0)*(ix<(xm-1))*(iy>0)*(iy<(ym-1)); sind0=sind0[fp]
         
    # #resolve flats         
    # print('---------resolve DEM flats------------------------------------')
    # isum=S.search_upstream(sind0,ireturn=2)
    # S.resolve_flat(sind0[isum==0])    
              
    # #identify depression catchment
    # sind0=nonzero(S.dir.ravel()==0)[0]; iy,ix=unravel_index(sind0,ds)
    # fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); sind0=sind0[fp]
    
    # #search and mark each depression
    # print('---------identify and mark depressions------------------------')
    # slen=len(sind0); seg0=arange(slen)+1; h0=S.dem.ravel()[sind0];  
    # S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max)
    
    # #get indices for each depression; here seg is numbering, not segment number
    # print('---------save all depression points---------------------------')
    # sind_segs=S.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=level_max)
    # ns0=array([len(i) for i in sind_segs])                  
  
    # #get depression boundary
    # print('---------compute depression boundary--------------------------')
    # S.compute_boundary(sind=sind0); 

    
#------------------------------------------------------------------------------    
    
    
    # S=dem(); S.read_deminfo('GEBCO.asc',subdomain_size=1e6,offset=10)
    # S0=dem(); S0.read_data('S1_DEM.npz')
    # S.read_demdata();
    # S.domains[5].read_demdata(data=S.dem)

#     #init
#     S=dem(); S.read_data('S1_m.npz')
#     ds=S.info.ds; ym,xm=ds; level_max=100; 
# # # #--------------fill depression in global--------------------------------------   
#     #-----------------------this part assign dir directly----------------------
#     #bndinfo
#     sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds); fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); 
#     sind0=sind0[fp]; dem0=S.info.dem_bnd_local[fp]; dir0=S.info.dir_bnd_local[fp]; #original
#     dir=S.dir.ravel()[sind0] #at present
         
#     #put flow into another seg if its original dir is not zero, it doesn't form loops    
#     fpz=nonzero((dir0!=0)*(dir==0))[0]; 
#     S.dir.ravel()[sind0[fpz]]=dir0[fpz]
    
#     #excude pts that forms loops          
#     sind_list,flag_loop=S.search_downstream(sind0[fpz],ireturn=3); 
#     fpl=nonzero(flag_loop==1)[0]; sindl=sind0[fpz[fpl]]; deml=dem0[fpz[fpl]] 
#     sind_list=array([intersect1d(sindl,i) for i in sind_list[fpl]])   
#     sind_all=[]; ids=[]; id1=0; id2=0;  
#     for i in arange(len(fpl)):            
#         sindi=unique(sind_list[i]); id2=id1+len(sindi)
#         sind_all.extend(sindi)        
#         ids.append(arange(id1,id2).astype('int')); id1=id1+len(sindi) 
#     sind_all=array(sind_all)
#     sindu,fpu=unique(sind_all,return_inverse=True); sindc,iA,iB=intersect1d(sindu,sindl,return_indices=True)
#     if not array_equal(sindu,sindc): sys.exit('sindc!=sindu') 
#     dem_all=deml[iB][fpu]
#     sind_min=unique(array([sind_all[id[nonzero(dem_all[id]==min(dem_all[id]))[0]]] for id in ids]))
#     S.dir.ravel()[sind_min]=0
       
#     #-----------------------this part assign dir to neighboring segs of dir=0--
#     while True:      
#         #identify depression catchment
#         sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
#         fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(S.dir.ravel()[sind0]==0); 
#         sind0=sind0[fp]; h0=S.info.dem_bnd_local[fp]
                                    
#         #search and mark each depression
#         print('---------identify and mark depressions------------------------')
#         slen=len(sind0); seg0=arange(slen)+1
#         S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max,msg=False)
        
#         #find all the neighboring indices with minimum depth seg 
#         sind_min,sind0_min,h0_min, dir_min=S.search_flat(sind0,ireturn=8,method=1)        
#         if sum(sind_min!=0)==0: break        
#         #reverse dir first
#         dir_min0=dir_min.copy(); dir_min[:]=0
#         dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
#         for i in arange(8):
#             fpr=dir_min0==dir_0[i]; dir_min[fpr]=dir_inv[i] 
            
#         #assign dir to the nearest seg with minimum depth; if h0=h0_min, use smaller sind0     
#         fpm=nonzero(((h0>h0_min)*(sind_min!=0))|((h0==h0_min)*(sind_min!=0)*(sind0<sind0_min)))[0]
#         if len(fpm)==0: fpm=nonzero((h0==h0_min)*(sind_min!=0)*(sind0>sind0_min))[0]
#         if len(fpm)==0: break
#         S.dir.ravel()[sind0[fpm]]=dir_min[fpm]
#         sind_list,flag_loop=S.search_downstream(sind0[fpm],ireturn=3)
#         if sum(flag_loop!=0)!=0: sys.exit('loop found: impossible')        
                        
        
#     S.read_demdata();
#     S.fill_depression()
#     S.compute_watershed()
#     S.compute_river(acc_limit=1e3)
#     S.write_shapefile('rivers','A1_2_rivers')  
#     sys.exit()
    
#     #pre-define variables       
#     ds=S.info.ds; ym,xm=ds; level_max=100; method=2
            
#     #identify depression catchment
#     sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
#     fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(S.dir.ravel()[sind0]==0); 
#     sind0=sind0[fp]; h0=S.info.dem_bnd_local[fp]
    
                            
#     #search and mark each depression
#     print('---------identify and mark depressions------------------------')
#     slen=len(sind0); seg0=arange(slen)+1
#     S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max)
    
    
#     #get indices for each depression; here seg is numbering, not segment number
#     print('---------save all depression points---------------------------')
#     sind_segs=S.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=level_max)
#     ns0=array([len(i) for i in sind_segs])
                 
#     #get depression boundary
#     print('---------compute depression boundary--------------------------')
#     S.compute_boundary(sind=sind0); 
                
#     #loop to reverse dir along streams
#     print('---------fill depressions-------------------------------------')
#     ids=arange(slen); iflag=0
#     while len(sind0)!=0:
#         iflag=iflag+1
#         print('fill depression: loop={}, ndep={}'.format(iflag,slen))
#         #-------------------------------------------------------------------------
#         #seg0,     ns0,     h0,      sind0,       sind_bnd
#         #seg_min,  ns_min,  h0_min,  sind0_min,   sind_min
#         #-------------------------------------------------------------------------        
        
#         #exclude nonboundary indices
#         sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
#         for i in arange(len(sind0)):            
#             sindi=unique(S.boundary[i]); id2=id1+len(sindi)
#             sind_bnd_all.extend(sindi)        
#             ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)                         
#         sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd)
#         flag_bnd_all=S.search_flat(sind_bnd_all,ireturn=10,method=method)
#         for i in arange(slen):
#             S.boundary[i]=sind_bnd_all[ids_bnd[i][flag_bnd_all[ids_bnd[i]]]]
                           
#         #recalcuate bnd for seg with false boundary; caused by some segs resides some other segs
#         len_seg=array([len(i) for i in sind_segs]); 
#         len_bnd=array([len(i) for i in S.boundary])
#         idz=nonzero((len_bnd==0)*(len_seg!=0))[0]
#         if len(idz)!=0:
#             #save boundary first
#             boundary=S.boundary.copy(); delattr(S,'boundary')
#             S.compute_boundary(sind=sind0[idz]);
#             boundary[idz]=S.boundary
#             S.boundary=boundary; boundary=None
        
#         #rearange the boundary index
#         sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
#         for i in arange(len(sind0)):            
#             sindi=S.boundary[i]; id2=id1+len(sindi)
#             sind_bnd_all.extend(sindi)        
#             ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)             
#         sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd);
        
#         #find the shorest route        
#         len_stream=S.search_downstream(sind_bnd_all,ireturn=4,msg=False)
#         for i in arange(slen):
#             ind_sort=argsort(len_stream[ids_bnd[i]])
#             sind_bnd_all[ids_bnd[i]]=sind_bnd_all[ids_bnd[i][ind_sort]]
                
#         #find all the neighboring indices with minimum depth seg 
#         sind_min_all,sind0_min_all,h0_min_all, dir_min_all=S.search_flat(sind_bnd_all,ireturn=8,method=1)
                        
#         #seg with minimum depth
#         h0_min=array([h0_min_all[id].min() for id in ids_bnd])        
#         mind=array([nonzero(h0_min_all[id]==hi)[0][0] for id,hi in zip(ids_bnd,h0_min)])        
#         sind_bnd=array([sind_bnd_all[id][mi] for id,mi in zip(ids_bnd,mind)]); 
#         sind_min=array([sind_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
#         sind0_min=array([sind0_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
#         dir_min=array([dir_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
#         seg_min=S.seg.ravel()[sind_min]; fps=nonzero(seg_min!=0)[0]; 
                    
#         #to find ns_min
#         ind_sort=argsort(seg_min[fps]);  
#         seg_1, ind_unique=unique(seg_min[fps[ind_sort]],return_inverse=True)
#         seg_2,iA,iB=intersect1d(seg_1,seg0,return_indices=True)        
#         ids_min=zeros(slen).astype('int'); ids_min[fps[ind_sort]]=ids[iB][ind_unique]
#         ns_min=zeros(slen).astype('int');    ns_min[fps]=ns0[ids_min[fps]]
             
#         #get stream from head to catchment
#         fp1=h0_min<h0
#         fp2=(h0_min>=h0)*(seg_min==0)
#         fp3=(h0_min>=h0)*(seg_min!=0)*(ns_min>ns0)
#         fp4=(h0_min>=h0)*(seg_min!=0)*(ns_min==ns0)*(sind0>sind0_min)        
#         fph=nonzero(fp1|fp2|fp3|fp4)[0]; sind_head=sind_bnd[fph]; 
#         sind_streams=S.search_downstream(sind_head,ireturn=2,msg=False)        
        
#         #get all stream index and its dir
#         sind=[]; dir=[];
#         for i in arange(len(fph)):
#             id=fph[i];    
#             #S.seg.ravel()[sind_segs[id]]=seg_min[id]; seg0[id]=seg_min[id]
#             sind_stream=sind_streams[i]
#             dir_stream=r_[dir_min[id],S.dir.ravel()[sind_stream][:-1]]            
#             sind.extend(sind_stream); dir.extend(dir_stream)
#         sind=array(sind); dir0=array(dir).copy(); dir=zeros(len(dir0)).astype('int')
            
#         #reverse dir
#         dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
#         for i in arange(8):
#             fpr=dir0==dir_0[i]; dir[fpr]=dir_inv[i]
#         S.dir.ravel()[sind]=dir;
                
#         #----build the linkage--------------------------------------------------
#         s_0=seg0.copy(); d_0=seg_min.copy(); d_0[setdiff1d(arange(slen),fph)]=-1
#         while True:         
#             fpz=nonzero((d_0!=0)*(d_0!=-1))[0] 
#             if len(fpz)==0: break         
        
#             #assign new value of d_0
#             s1=d_0[fpz].copy(); 
                        
#             ind_sort=argsort(s1); 
#             s2,ind_unique=unique(s1[ind_sort],return_inverse=True)
#             s3,iA,iB=intersect1d(s2,s_0,return_indices=True)            
#             d_0[fpz[ind_sort]]=d_0[iB[ind_unique]]
            
#             #assign new value fo s_0
#             s_0[fpz]=s1;
        
#         #--------------------------
#         seg_stream=seg0[fph[d_0[fph]==-1]] #seg that flows to another seg (!=0)        
#         seg_tmp,iA,sid=intersect1d(seg_stream,seg0,return_indices=True)
        
#         seg_target=s_0[fph[d_0[fph]==-1]]; tid=zeros(len(seg_target)).astype('int'); 
#         ind_sort=argsort(seg_target); seg_tmp, ind_unique=unique(seg_target[ind_sort],return_inverse=True)
#         seg_tmp,iA,iB=intersect1d(seg_target,seg0,return_indices=True);
#         tid[ind_sort]=iB[ind_unique]
#         #----------------------------------------------------------------------
                    
#         #reset variables-----
#         ids_stream=ids[fph]; ids_left=setdiff1d(ids,ids_stream)        
    
#         #collect boundary        
#         for si,ti in zip(sid,tid):                        
#             S.seg.ravel()[sind_segs[si]]=seg0[ti]
#             S.boundary[ti]=r_[S.boundary[ti],S.boundary[si]]
#             sind_segs[ti]=r_[sind_segs[ti],sind_segs[si]]
#             ns0[ti]=ns0[ti]+ns0[si]
               
#         #set other seg number to zeros
#         seg_stream2=seg0[fph[d_0[fph]==0]] #seg that flows to another seg (!=0)        
#         seg_tmp,iA,sid2=intersect1d(seg_stream2,seg0,return_indices=True)
#         for si in sid2:
#             S.seg.ravel()[sind_segs[si]]=0
        
#         #update variables    
#         sind0=sind0[ids_left]; seg0=seg0[ids_left]; h0=h0[ids_left]; ns0=ns0[ids_left]
#         S.boundary=S.boundary[ids_left]; sind_segs=sind_segs[ids_left]
#         slen=len(sind0); ids=arange(slen)
#     #clean
#     delattr(S,'seg');delattr(S,'boundary')

    
#     S.compute_watershed()
#     S.compute_river(seg,acc_limit=1e3)
#     S.write_shapefile('rivers','A1_2_rivers')  
 


#     #init
#     S=dem(); S.read_data('S9_m.npz')
#     ds=S.info.ds; ym,xm=ds; level_max=100; 
    
#     # S.fill_depression_global(level_max=50)

# # # #--------------fill depression in global--------------------------------------   
#     #-----------------------this part assign dir directly----------------------
#     #bndinfo
#     sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds); fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); 
#     sind0=sind0[fp]; dem0=S.info.dem_bnd_local[fp]; dir0=S.info.dir_bnd_local[fp]; #original
#     dir=S.dir.ravel()[sind0] #at present
         
#     #put flow into another seg if its original dir is not zero, it doesn't form loops    
#     fpz=nonzero((dir0!=0)*(dir==0))[0]; 
#     S.dir.ravel()[sind0[fpz]]=dir0[fpz]
    
#     #excude pts that forms loops          
#     sind_list0,flag_loop=S.search_downstream(sind0[fpz],ireturn=3); 
#     fpl=nonzero(flag_loop==1)[0]; sindl=sind0[fpz[fpl]]; deml=dem0[fpz[fpl]] 
#     sind_list=array([intersect1d(sindl,i) for i in sind_list0[fpl]])
    
#     sind_all=[]; ids=[]; id1=0; id2=0;  
#     for i in arange(len(fpl)):            
#         sindi=unique(sind_list[i]); id2=id1+len(sindi)
#         sind_all.extend(sindi)        
#         ids.append(arange(id1,id2).astype('int')); id1=id1+len(sindi) 
#     sind_all=array(sind_all)
#     sindu,fpu=unique(sind_all,return_inverse=True); sindc,iA,iB=intersect1d(sindu,sindl,return_indices=True)
#     if not array_equal(sindu,sindc): sys.exit('sindc!=sindu') 
#     dem_all=deml[iB][fpu]
#     sind_min=unique(array([sind_all[id[nonzero(dem_all[id]==min(dem_all[id]))[0]]] for id in ids]))
#     S.dir.ravel()[sind_min]=0
    
#     sys.exit()
    
#     S.fill_depression()
 
#     S.compute_watershed()
    
#     sys.exit();
       
    # #-----------------------this part assign dir to neighboring segs of dir=0--
    # while True:      
    #     #identify depression catchment
    #     sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
    #     fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(S.dir.ravel()[sind0]==0); 
    #     sind0=sind0[fp]; h0=S.info.dem_bnd_local[fp]
                                    
    #     #search and mark each depression
    #     print('---------identify and mark depressions------------------------')
    #     slen=len(sind0); seg0=arange(slen)+1
    #     S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max,msg=True)
        
    #     #find all the neighboring indices with minimum depth seg 
    #     sind_min,sind0_min,h0_min, dir_min=S.search_flat(sind0,ireturn=8,method=1)        
    #     if sum(sind_min!=0)==0: break        
    #     #reverse dir first
    #     dir_min0=dir_min.copy(); dir_min[:]=0
    #     dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
    #     for i in arange(8):
    #         fpr=dir_min0==dir_0[i]; dir_min[fpr]=dir_inv[i] 
            
    #     #assign dir to the nearest seg with minimum depth; if h0=h0_min, use smaller sind0     
    #     fpm=nonzero(((h0>h0_min)*(sind_min!=0))|((h0==h0_min)*(sind_min!=0)*(sind0<sind0_min)))[0]
    #     if len(fpm)==0: fpm=nonzero((h0==h0_min)*(sind_min!=0)*(sind0>sind0_min))[0]
    #     if len(fpm)==0: break
    #     S.dir.ravel()[sind0[fpm]]=dir_min[fpm]
    #     sind_list,flag_loop=S.search_downstream(sind0[fpm],ireturn=3)
    #     if sum(flag_loop!=0)!=0: sys.exit('loop found: impossible')    
    
    # seg=arange(1,1e5)
    # S.compute_watershed()
    # S.compute_river(seg,acc_limit=1e3)
    # S.write_shapefile('rivers','B1_1_rivers')
    
# # #--------------fill depression in global--------------------------------------

    # #pre-define variables       
    # ds=S.info.ds; ym,xm=ds; level_max=100; method=2
            
    # #identify depression catchment
    # sind0=S.info.sind_bnd_local; iy,ix=unravel_index(sind0,ds)
    # fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1))*(S.dir.ravel()[sind0]==0); 
    # sind0=sind0[fp]; h0=S.info.dem_bnd_local[fp]
                        
    # #search and mark each depression
    # print('---------identify and mark depressions------------------------')
    # slen=len(sind0); seg0=arange(slen)+1
    # S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=level_max)
    
    # #get indices for each depression; here seg is numbering, not segment number
    # print('---------save all depression points---------------------------')
    # sind_segs=S.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=level_max)
    # ns0=array([len(i) for i in sind_segs])
                 
    # #get depression boundary
    # print('---------compute depression boundary--------------------------')
    # S.compute_boundary(sind=sind0); 
                
    # #loop to reverse dir along streams
    # print('---------fill depressions-------------------------------------')
    # ids=arange(slen); iflag=0
    # while len(sind0)!=0:
    #     iflag=iflag+1
    #     print('fill depression: loop={}, ndep={}'.format(iflag,slen))
    #     #-------------------------------------------------------------------------
    #     #seg0,     ns0,     h0,      sind0,       sind_bnd
    #     #seg_min,  ns_min,  h0_min,  sind0_min,   sind_min
    #     #-------------------------------------------------------------------------        
        
    #     #exclude nonboundary indices
    #     sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
    #     for i in arange(len(sind0)):            
    #         sindi=unique(S.boundary[i]); id2=id1+len(sindi)
    #         sind_bnd_all.extend(sindi)        
    #         ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)                         
    #     sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd)
    #     flag_bnd_all=S.search_flat(sind_bnd_all,ireturn=10,method=method)
    #     for i in arange(slen):
    #         S.boundary[i]=sind_bnd_all[ids_bnd[i][flag_bnd_all[ids_bnd[i]]]]
                           
    #     #recalcuate bnd for seg with false boundary; caused by some segs resides some other segs
    #     len_seg=array([len(i) for i in sind_segs]); 
    #     len_bnd=array([len(i) for i in S.boundary])
    #     idz=nonzero((len_bnd==0)*(len_seg!=0))[0]
    #     if len(idz)!=0:
    #         #save boundary first
    #         boundary=S.boundary.copy(); delattr(S,'boundary')
    #         S.compute_boundary(sind=sind0[idz]);
    #         boundary[idz]=S.boundary
    #         S.boundary=boundary; boundary=None
        
    #     #rearange the boundary index
    #     sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
    #     for i in arange(len(sind0)):            
    #         sindi=S.boundary[i]; id2=id1+len(sindi)
    #         sind_bnd_all.extend(sindi)        
    #         ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)             
    #     sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd);
        
    #     #find the shorest route        
    #     len_stream=S.search_downstream(sind_bnd_all,ireturn=4,msg=False)
    #     for i in arange(slen):
    #         ind_sort=argsort(len_stream[ids_bnd[i]])
    #         sind_bnd_all[ids_bnd[i]]=sind_bnd_all[ids_bnd[i][ind_sort]]
                
    #     #find all the neighboring indices with minimum depth seg 
    #     sind_min_all,sind0_min_all,h0_min_all, dir_min_all=S.search_flat(sind_bnd_all,ireturn=8,method=1)
                        
    #     #seg with minimum depth
    #     h0_min=array([h0_min_all[id].min() for id in ids_bnd])        
    #     mind=array([nonzero(h0_min_all[id]==hi)[0][0] for id,hi in zip(ids_bnd,h0_min)])        
    #     sind_bnd=array([sind_bnd_all[id][mi] for id,mi in zip(ids_bnd,mind)]); 
    #     sind_min=array([sind_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
    #     sind0_min=array([sind0_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
    #     dir_min=array([dir_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
    #     seg_min=S.seg.ravel()[sind_min]; fps=nonzero(seg_min!=0)[0]; 
                    
    #     #to find ns_min
    #     ind_sort=argsort(seg_min[fps]);  
    #     seg_1, ind_unique=unique(seg_min[fps[ind_sort]],return_inverse=True)
    #     seg_2,iA,iB=intersect1d(seg_1,seg0,return_indices=True)        
    #     ids_min=zeros(slen).astype('int'); ids_min[fps[ind_sort]]=ids[iB][ind_unique]
    #     ns_min=zeros(slen).astype('int');    ns_min[fps]=ns0[ids_min[fps]]
             
    #     #get stream from head to catchment
    #     fp1=h0_min<h0
    #     fp2=(h0_min>=h0)*(seg_min==0)
    #     fp3=(h0_min>=h0)*(seg_min!=0)*(ns_min>ns0)
    #     fp4=(h0_min>=h0)*(seg_min!=0)*(ns_min==ns0)*(sind0>sind0_min)        
    #     fph=nonzero(fp1|fp2|fp3|fp4)[0]; sind_head=sind_bnd[fph]; 
    #     sind_streams=S.search_downstream(sind_head,ireturn=2,msg=False)        
        
    #     #get all stream index and its dir
    #     sind=[]; dir=[];
    #     for i in arange(len(fph)):
    #         id=fph[i];    
    #         #S.seg.ravel()[sind_segs[id]]=seg_min[id]; seg0[id]=seg_min[id]
    #         sind_stream=sind_streams[i]
    #         dir_stream=r_[dir_min[id],S.dir.ravel()[sind_stream][:-1]]            
    #         sind.extend(sind_stream); dir.extend(dir_stream)
    #     sind=array(sind); dir0=array(dir).copy(); dir=zeros(len(dir0)).astype('int')
            
    #     #reverse dir
    #     dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
    #     for i in arange(8):
    #         fpr=dir0==dir_0[i]; dir[fpr]=dir_inv[i]
    #     S.dir.ravel()[sind]=dir;
                
    #     #----build the linkage--------------------------------------------------
    #     s_0=seg0.copy(); d_0=seg_min.copy(); d_0[setdiff1d(arange(slen),fph)]=-1
    #     while True:         
    #         fpz=nonzero((d_0!=0)*(d_0!=-1))[0] 
    #         if len(fpz)==0: break         
        
    #         #assign new value of d_0
    #         s1=d_0[fpz].copy(); 
                        
    #         ind_sort=argsort(s1); 
    #         s2,ind_unique=unique(s1[ind_sort],return_inverse=True)
    #         s3,iA,iB=intersect1d(s2,s_0,return_indices=True)            
    #         d_0[fpz[ind_sort]]=d_0[iB[ind_unique]]
            
    #         #assign new value fo s_0
    #         s_0[fpz]=s1;
        
    #     #--------------------------
    #     seg_stream=seg0[fph[d_0[fph]==-1]] #seg that flows to another seg (!=0)        
    #     seg_tmp,iA,sid=intersect1d(seg_stream,seg0,return_indices=True)
        
    #     seg_target=s_0[fph[d_0[fph]==-1]]; tid=zeros(len(seg_target)).astype('int'); 
    #     ind_sort=argsort(seg_target); seg_tmp, ind_unique=unique(seg_target[ind_sort],return_inverse=True)
    #     seg_tmp,iA,iB=intersect1d(seg_target,seg0,return_indices=True);
    #     tid[ind_sort]=iB[ind_unique]
    #     #----------------------------------------------------------------------
                    
    #     #reset variables-----
    #     ids_stream=ids[fph]; ids_left=setdiff1d(ids,ids_stream)        
    
    #     #collect boundary        
    #     for si,ti in zip(sid,tid):                        
    #         S.seg.ravel()[sind_segs[si]]=seg0[ti]
    #         S.boundary[ti]=r_[S.boundary[ti],S.boundary[si]]
    #         sind_segs[ti]=r_[sind_segs[ti],sind_segs[si]]
    #         ns0[ti]=ns0[ti]+ns0[si]
               
    #     #set other seg number to zeros
    #     seg_stream2=seg0[fph[d_0[fph]==0]] #seg that flows to another seg (!=0)        
    #     seg_tmp,iA,sid2=intersect1d(seg_stream2,seg0,return_indices=True)
    #     for si in sid2:
    #         S.seg.ravel()[sind_segs[si]]=0
        
    #     #update variables    
    #     sind0=sind0[ids_left]; seg0=seg0[ids_left]; h0=h0[ids_left]; ns0=ns0[ids_left]
    #     S.boundary=S.boundary[ids_left]; sind_segs=sind_segs[ids_left]
    #     slen=len(sind0); ids=arange(slen)
    # #clean
    # delattr(S,'seg');delattr(S,'boundary')


#------read dem----------------------------------------------------------------
    acc_limit=1e3; seg=arange(1,1e5)
    S=dem(); 
    t0=time.time();
    #--------------------------------------------------------------------------
    # S.read_deminfo('GEBCO.asc',subdomain_size=5e5,offset=1)
    # # S.read_demdata()
    # S.read_data('S1_DEM.npz')
  
    S.read_deminfo('ne_atl_crm_v1.asc',subdomain_size=1e6,offset=1)
    S.read_demdata()
    sys.exit()
    S.read_data('S2_DEM.npz')
    
    S.read_deminfo('13arcs/southern_louisiana_13_navd88_2010.asc',subdomain_size=1e10,offset=1)
    S.read_data('S4.npz')
    
    sys.exit();
    S.read_demdata()
    
    S.save_data('S3_DEM', ['dem'])
    
    print('-------------nsubdomain={}-----------------------------------------'.format(S.info.nsubdomain))
    #compute dir on each subdomain
    for i in arange(S.info.nsubdomain):
        t1=time.time();
        print('--------------------------------------------------------------')
        print('---------work on subdomain depression: {}---------------------'.format(i))
        print('--------------------------------------------------------------')
                
        Si=S.domains[i]; 
        Si.read_demdata(data=S.dem)    
        Si.compute_dir();
        
        #if Si is a subdomain, save bnd info for collecting
        if S.info.nsubdomain>1:            
            Si.collapse_subdomain();              
            Si.change_bnd_dir()     
               
        #resolve flat and fill depression
        Si.fill_depression(level_max=100,method=0)
        print('time={}, {}'.format(time.time()-t1,time.time()-t0))
        
    #collect dir
    S.collect_subdomain_data(name='dir',outname='dir')
    
    #save info
    S.save_data('S10_m',['dem','dir','info'])
    
    if S.info.nsubdomain>1:
        #global domain
        print('--------------------------------------------------------------')
        print('---------work on global domain depression---------------------')
        print('--------------------------------------------------------------')
        S.fill_depression_global() 
    
    S.compute_watershed()
    S.compute_river(seg,acc_limit=acc_limit)
    S.write_shapefile('rivers','C1_0_rivers')
    
    dt=time.time()-t0
           
    # ---------------------------assign dir0 first------------------------------
    # S=dem(); S.read_data('S1_m.npz')
    
    # #deal with bndinfo
    # sind0=S.info.sind_bnd_local; dem0=S.info.dem_bnd_local; dir0=S.info.dir_bnd_local; 
    # dir=S.dir.ravel()[sind0]
    
    # #put flow into another seg if its original dir is not zero
    # fpz=nonzero((dir0!=0)*(dir==0))[0];  sindz=sind0[fpz]; 
    
    # #find the depth(dir=0) of the seg receiving flow 
    # S.dir.ravel()[sindz]=dir0[fpz]
    # sind_next=S.search_downstream(sindz,ireturn=0)
   
    # S.dir.ravel()[sindz]=0 #reset back to zero     
    # sind_next=S.search_downstream(sind_next,ireturn=1) 
    
    # #unique index
    # sindu,fpu=unique(sind_next,return_inverse=True)
    # sind,iA,iB=intersect1d(sind0,sindu,return_indices=True)
    # dem=dem0[iA][fpu]
    
    # #assign dir0
    # fpa=nonzero(dem0[fpz]>dem)[0]; S.dir.ravel()[sindz[fpa]]=dir0[fpz[fpa]] 
                   
    # #fill depression
    # delattr(S,'dem')
    
        
    # S.read_data('S1_m.npz')
    # S.fill_depression_global(level_max=100)
    # S.read_demdata(); S.fill_depression();
    
    #--------------------------------------------
    # S.compute_watershed()
    # S.compute_river(seg,acc_limit=acc_limit)
    # S.write_shapefile('rivers','B1_1_rivers')
    
    # dt=time.time()-t0
    # # # S.compute_boundary(seg,acc_limit=acc_limit)   
    
#------write shapefile---------------------------------------------------------
    # acc_limit=1e4; seg=arange(1,1e5)
    # S0=dem_dir(); S0.read_data('S1.npz')
    
    # S=dem_dir(); 
    # S.read_data('S2_DEM.npz'); S.affine=S0.affine
    # S.compute_dir()
    # S.fill_depression(level_max=100)
    # S.compute_watershed()
      
    # S.compute_river(seg,acc_limit=acc_limit)
    # S.write_shapefile('rivers','A0_rivers')
    # # S.compute_boundary(seg,acc_limit=acc_limit)            
    # # S.write_shapefile('boundary','B_boundary')    S

#--------------------------precalculation--------------------------------------
    # # # # # # # # #--------------------------------------------------------------
    # # # compute dir and acc, then save them
    # # # fname='./13arcs/southern_louisiana_13_navd88_2010.asc'; sname='S3'
    # # # fname='ne_atl_crm_v1.asc'; sname='S2'
    # fname='GEBCO.asc'; sname='S1'
        
    # #read dem info
    # gds=read_deminfo(fname,'dem',size_subdomain=1e7); 
    # gds.add_deminfo(fname,'dem0',size_subdomain=1e9); 
    
    # #read all data first
    # gds.read_dem_data('dem0')  
    
    # flat_option=0

    # S=dem_dir();
    # #reconstrcut data from subdomains
    # id=-1; print(gds.dem_info.nsubdomain)
    # for i in arange(gds.dem_info.ny):
    #     for j in arange(gds.dem_info.nx):            
    #         id=id+1;  print(id)
            
    #         #read dem,            
    #         gds.read_dem_data('dem',[id],dem_data=gds.dem0_data[0].data);
    #         # gds.read_dem_data('dem',[id]);
    #         gd=gds.dem_data[0]

    #         #processing raw data
    #         if flat_option==0:
    #             try:                
    #                 gd.fill_depressions(gd.data, out_name='fdem')
    #                 try:
    #                     gd.resolve_flats(gd.fdem,'flats')
    #                 except:
    #                     gd.flats=gd.fdem
    #             except:
    #                 try:
    #                     gd.resolve_flats(gd.data,'flats')
    #                 except:
    #                     gd.flats=gd.data
    #         elif flat_option==1:
    #             #don't use resolve flats
    #             try:                
    #                 gd.fill_depressions(gd.data, out_name='fdem')    
    #                 gd.flats=gd.fdem
    #             except:      
    #                 gd.flats=gd.data
            
    #         #local data
    #         ixy=gds.dem_info.domains[id].rind            
    #         demii=array(gd.flats[ixy[0]:ixy[1],ixy[2]:ixy[3]])
            
    #         if j==0:
    #             demi=demii
    #         else:
    #             demi=c_[demi,demii]
    #     #vertical
    #     if i==0:
    #         dem=demi
    #     else:
    #         dem=r_[dem,demi]
                
    #     #vertical
    #     if i==0:
    #         S.dem=demi
    #     else:
    #         S.dem=r_[S.dem,demi]
    
    # #save information
    # S.nodata=gd.nodata; S.ds=S.dem.shape; S.affine=[*gds.dem_info.affine]
    # S.compute_extent();
        
    # #compute dir
    # t0=time.time();
    # S.compute_dir(S.dem,nodata=S.nodata);
    # S.compute_watershed()
    # dt=time.time()-t0
    
    # # S.save_data(sname,['dir','acc','seg','nodata','extent','ds','affine'])
    # #add mask
    # S.mask=(S.dem>=0)*(S.dem<=50)
    # S.save_data(sname,['dir','acc','seg','nodata','extent','ds','affine','mask'])
    
#------------------------plot rivers and seg boundary--------------------------
    # S=dem_dir(); S.read_data('S1.npz'); 
    
    # acc_limit=1e3; seg=arange(1,10)
    # S.compute_river(seg,acc_limit=acc_limit)
    # S.compute_boundary(seg,acc_limit=acc_limit)
    

    # figure();        
    # #plot acc
    # imshow(S.acc,vmin=0,vmax=5e3,extent=S.extent)
    
    # #plot rivers
    # for i in arange(len(S.rivers)):
    #     sindi=S.rivers[i].copy();
    #     yi,xi=S.get_coordinates(sindi)
        
    #     fp=(xi==S.nodata)|(yi==S.nodata);
    #     xi[fp]=nan; yi[fp]=nan;
        
    #     plot(xi,yi,'r-')

    # #plot river mouths
    # yi,xi=S.get_coordinates(S.info.rind)
    # plot(xi,yi,'b*',ms=12)
    
    # #plot seg boundary
    # colors='www'
    # for i in arange(len(S.boundary)):
    #     sindi=S.boundary[i];
    #     # sindi=array(S.sind_list[i])
    #     yi,xi=S.get_coordinates(array(sindi))
        
    #     fp=(xi==S.nodata)|(yi==S.nodata);
    #     xi[fp]=nan; yi[fp]=nan;
        
    #     plot(xi,yi,color=colors[mod(i,3)],lw=1)    
    
    
#---------------test method "search_downstream---------------------------------
    # S=dem_dir(); S.read_data('S1.npz'); S.compute_extent();
    
    # sind0=ravel_multi_index(nonzero((S.seg<=10)*(S.seg>0)*(S.dir==0)),S.ds);   
    
    # sind_up=S.search_upstream(sind0,ireturn=6)
    # list_down=S.search_downstream(sind_up,ireturn=2)
    # list_up=S.search_upstream(sind0,ireturn=7)
    
    # dyi,dxi=S.get_coordinates(sind0)
    # uyi,uxi=S.get_coordinates(sind_up)
    
    # figure();     
    # subplot(2,1,1)
    # imshow(S.acc,vmin=0,vmax=1e2,extent=S.extent)
    # plot(dxi,dyi,'b*',uxi,uyi,'w*')
    # for i in arange(len(sind0)):
    #     sindi=list_down[i];
    #     yi,xi=S.get_coordinates(sindi)
        
    #     fp=(xi==S.nodata)|(yi==S.nodata);
    #     xi[fp]=nan; yi[fp]=nan;
        
    #     plot(xi,yi,'r-')        
    
        
    # subplot(2,1,2)
    # imshow(S.acc,vmin=0,vmax=1e2,extent=S.extent)    
    # plot(dxi,dyi,'b*',uxi,uyi,'w*')
    # for i in arange(len(sind0)):
    #     sindi=list_up[i];
    #     yi,xi=S.get_coordinates(sindi)
        
    #     fp=(xi==S.nodata)|(yi==S.nodata);
    #     xi[fp]=nan; yi[fp]=nan;
        
    #     plot(xi,yi,'r-')    

#-------------------------test fill depression---------------------------------
    # S=dem_dir(); S.read_data('S1_flats_fdem.npz'); S.ds=S.dem.shape; ds=S.ds; ym,xm=ds
    # dzm=min(diff(unique(S.dem)))*0.9; S.remove_nan_nodata();
        
    # S.compute_dir(method=0);
    
    # #resolve flats 
    # sind0=nonzero(S.dir.ravel()==0)[0]; 
    # isum=S.search_upstream(sind0,ireturn=2)
    # S.resolve_flat(sind0[isum==0])    

    # #resolve flats for single cells
    # sind0=nonzero(S.dir.ravel()==0)[0]; 
    # isum=S.search_upstream(sind0,ireturn=2)    
    # S.search_flat(sind0[isum==0],ireturn=6)
          
    # #identify depression catchment
    # sind0=nonzero(S.dir.ravel()==0)[0]; iy,ix=unravel_index(sind0,ds)
    # fp=(iy>0)*(iy<(ym-1))*(ix>0)*(ix<(xm-1)); sind0=sind0[fp]
    
    # #search and mark each depression
    # slen=len(sind0); seg0=arange(slen)+1; h0=S.dem.ravel()[sind0];  
    # S.search_upstream(sind0,ireturn=3,seg=seg0,level_max=25)
    
    # #get indices for each depression; here seg is numbering, not segment number
    # sind_segs=S.search_upstream(sind0,ireturn=9,seg=arange(slen),acc_calc=True,level_max=25)
    # ns0=array([len(i) for i in sind_segs])                  
  
    # #get depression boundary
    # S.compute_boundary(sind=sind0); 
        
    # #loop to reverse dir along streams
    # ids=arange(slen); iflag=0
    # while len(sind0)!=0:
    #     iflag=iflag+1
    #     print('fill depression: loop={}, ndep={}'.format(iflag,slen))
    #     # slen=len(ids); h0=h00[ids]; sind0=sind00[ids]; ns0=ns00[ids]
    #     # ids=arange(slen)
    #     #-------------------------------------------------------------------------
    #     #seg0,     ns0,     h0,      sind0,       sind_bnd,   h_bnd
    #     #seg_min,  ns_min,  h0_min,  sind0_min,   sind_min,   h_min  h_bnd_min  dir_min
    #     #-------------------------------------------------------------------------        
        
    #     #exclude nonboundary indices
    #     sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
    #     for i in arange(len(sind0)):            
    #         sindi=unique(S.boundary[i]); id2=id1+len(sindi)
    #         sind_bnd_all.extend(sindi)        
    #         ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)                         
    #     sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd)
    #     flag_bnd_all=S.search_flat(sind_bnd_all,ireturn=10)
    #     for i in arange(slen):
    #         S.boundary[i]=sind_bnd_all[ids_bnd[i][flag_bnd_all[ids_bnd[i]]]]
            
    #     #recalcuate bnd for seg with false boundary
    #     len_seg=array([len(i) for i in sind_segs]); 
    #     len_bnd=array([len(i) for i in S.boundary])
    #     idz=nonzero((len_bnd==0)*(len_seg!=0))[0]
    #     if len(idz)!=0:
    #         #save boundary first
    #         boundary=S.boundary.copy(); delattr(S,'boundary')
    #         S.compute_boundary(sind=sind0[idz],msg=False);
    #         boundary[idz]=S.boundary
    #         S.boundary=boundary; boundary=None
                                    
    #     #rearange the boundary index
    #     sind_bnd_all=[]; ids_bnd=[]; id1=0; id2=0;  
    #     for i in arange(len(sind0)):            
    #         sindi=S.boundary[i]; id2=id1+len(sindi)
    #         sind_bnd_all.extend(sindi)        
    #         ids_bnd.append(arange(id1,id2).astype('int')); id1=id1+len(sindi)             
    #     sind_bnd_all=array(sind_bnd_all);ids_bnd=array(ids_bnd);
        
    #     #find all the neighboring indices with minimum depth
    #     sind_min_all,h_min_all,dir_min_all=S.search_flat(sind_bnd_all,ireturn=8)
                
    #     #minimum for each seg
    #     h_min=array([h_min_all[id].min() for id in ids_bnd])
    #     mind=array([nonzero(h_min_all[id]==hi)[0][0] for id,hi in zip(ids_bnd,h_min)])        
    #     sind_bnd=array([sind_bnd_all[id][mi] for id,mi in zip(ids_bnd,mind)]); h_bnd=S.dem.ravel()[sind_bnd]
    #     sind_min=array([sind_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
    #     dir_min=array([dir_min_all[id][mi] for id,mi in zip(ids_bnd,mind)])
        
    #     #get s0_min,h0_min,sind0_min
    #     seg_min=S.seg.ravel()[sind_min]; fps=nonzero(seg_min!=0)[0]; 
                
    #     ind_sort=argsort(seg_min[fps]);  
    #     seg_1, ind_unique=unique(seg_min[fps[ind_sort]],return_inverse=True)
    #     seg_2,iA,iB=intersect1d(seg_1,seg0,return_indices=True)        
    #     ids_min=zeros(slen).astype('int'); ids_min[fps[ind_sort]]=ids[iB][ind_unique]
        
    #     ns_min=zeros(slen).astype('int');    ns_min[fps]=ns0[ids_min[fps]]
    #     h0_min=-1e5*ones(slen);              h0_min[fps]=h0[ids_min[fps]]
    #     sind0_min=-ones(slen).astype('int'); sind0_min[fps]=sind0[ids_min[fps]]
    #     h_bnd_min=zeros(slen);               h_bnd_min[fps]=h_bnd[ids_min[fps]]
    
    #     #get stream from head to catchment
    #     fp1=seg_min==0; 
    #     fp2=(seg_min!=0)*(h0_min<h0); 
    #     fp3=(seg_min!=0)*(h0_min==h0)*(ns_min>ns0)
    #     fp4=(seg_min!=0)*(h0_min==h0)*(ns_min==ns0)*(h_bnd>h_bnd_min); 
    #     fp5=(seg_min!=0)*(h0_min==h0)*(ns_min==ns0)*(h_bnd==h_bnd_min)*(sind0>sind0_min);         
    #     fph=nonzero(fp1|fp2|fp3|fp4|fp5)[0]; sind_head=sind_bnd[fph]; 
    #     sind_streams=S.search_downstream(sind_head,ireturn=2,msg=False)        
                
    #     #get all stream index and its dir
    #     t0=time.time(); sind=[]; dir=[];
    #     for i in arange(len(fph)):
    #         id=fph[i];    
    #         #S.seg.ravel()[sind_segs[id]]=seg_min[id]; seg0[id]=seg_min[id]
    #         sind_stream=sind_streams[i][:-1]
    #         dir_stream=r_[dir_min[id],S.dir.ravel()[sind_stream][:-1]]            
    #         sind.extend(sind_stream); dir.extend(dir_stream)
    #     sind=array(sind); dir0=array(dir).copy(); dir=zeros(len(dir0)).astype('int')
            
    #     #reverse dir
    #     dir_0=[128,64,32,16,8,4,2,1]; dir_inv=[8,4,2,1,128,64,32,16]
    #     for i in arange(8):
    #         fpr=dir0==dir_0[i]; dir[fpr]=dir_inv[i]
    #     dt=time.time()-t0
    #     S.dir.ravel()[sind]=dir;
        
    #     #----build the linkage--------------------------------------------------
    #     s_0=seg0.copy(); d_0=seg_min.copy(); d_0[setdiff1d(arange(slen),fph)]=-1
    #     while True:         
    #         fpz=nonzero((d_0!=0)*(d_0!=-1))[0] 
    #         if len(fpz)==0: break         
        
    #         #assign new value of d_0
    #         s1=d_0[fpz].copy(); 
                        
    #         ind_sort=argsort(s1); 
    #         s2,ind_unique=unique(s1[ind_sort],return_inverse=True)
    #         s3,iA,iB=intersect1d(s2,s_0,return_indices=True)            
    #         d_0[fpz[ind_sort]]=d_0[iB[ind_unique]]
            
    #         #assign new value fo s_0
    #         s_0[fpz]=s1;
        
    #     #--------------------------
    #     seg_stream=seg0[fph[d_0[fph]==-1]] #seg that flows to another seg (!=0)        
    #     seg_tmp,iA,sid=intersect1d(seg_stream,seg0,return_indices=True)
        
    #     seg_target=s_0[fph[d_0[fph]==-1]]; tid=zeros(len(seg_target)).astype('int'); 
    #     ind_sort=argsort(seg_target); seg_tmp, ind_unique=unique(seg_target[ind_sort],return_inverse=True)
    #     seg_tmp,iA,iB=intersect1d(seg_target,seg0,return_indices=True);
    #     tid[ind_sort]=iB[ind_unique]
    #     #----------------------------------------------------------------------
                    
    #     #reset variables-----
    #     ids_stream=ids[fph]; ids_left=setdiff1d(ids,ids_stream)        

    #     #collect boundary        
    #     for si,ti in zip(sid,tid):                        
    #         S.seg.ravel()[sind_segs[si]]=seg0[ti]
    #         S.boundary[ti]=r_[S.boundary[ti],S.boundary[si]]
    #         sind_segs[ti]=r_[sind_segs[ti],sind_segs[si]]
    #         ns0[ti]=ns0[ti]+ns0[si]
               
    #     #set other seg number to zeros
    #     seg_stream2=seg0[fph[d_0[fph]==0]] #seg that flows to another seg (!=0)        
    #     seg_tmp,iA,sid2=intersect1d(seg_stream2,seg0,return_indices=True)
    #     for si in sid2:
    #         S.seg.ravel()[sind_segs[si]]=0
        
    #     #update variables    
    #     sind0=sind0[ids_left]; seg0=seg0[ids_left]; h0=h0[ids_left]; ns0=ns0[ids_left]
    #     S.boundary=S.boundary[ids_left]; sind_segs=sind_segs[ids_left]
    #     slen=len(sind0); ids=arange(slen)    
            
    # #compute watershed
    # S.compute_watershed();
    # imshow(S.acc,vmin=0,vmax=1e3)
    